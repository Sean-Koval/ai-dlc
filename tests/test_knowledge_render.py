"""The ``wiki`` role, its Confluence provider and ``knowledge render`` (KAN-430).

An in-memory fake Confluence behind ``httpx.MockTransport`` stands in for the site; a
local git repository is the knowledge store. Nothing here reaches a live service.
"""

import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.contracts import manifest, validate_request, validate_response
from ai_dlc.documentation import knowledge_records
from ai_dlc.documentation.knowledge_render import HASH_PROPERTY, KnowledgeRender
from ai_dlc.errors import RefusedError
from ai_dlc.providers import Registry, confluence_cloud
from ai_dlc.providers.confluence_cloud import ConfluenceCloud, ConfluenceRefusal, storage

CLOUD = "11111111-2222-3333-4444-555555555555"
TOKEN = "s3cret-token-value"
WIKI = {
    "kind": "confluence-cloud",
    "site_url": "https://example.atlassian.net",
    "cloud_id": CLOUD,
    "space": "ENG",
    "parent_id": "1000",
    "auth_mode": "oauth_bearer",
    "token_env": "CONFLUENCE_TOKEN",
}
ENVIRON = {"CONFLUENCE_TOKEN": TOKEN}
WIKI_TOML = (
    '[format]\nversion = 1\n[wiki]\nsite = "example.atlassian.net"\n'
    'source = "https://github.com/example/knowledge/blob/main/"\n'
)


class FakeConfluence:
    """The slice of Confluence Cloud REST the provider uses, with versions and labels."""

    def __init__(self):
        self.pages: dict[str, dict] = {}
        self.next_id = 2000
        self.writes = 0
        self.requests: list[httpx.Request] = []

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handle))

    def _id(self) -> str:
        self.next_id += 1
        return str(self.next_id)

    def hand_edit(self, page_id: str, body: str = "<p>edited by hand</p>") -> None:
        page = self.pages[page_id]
        page["body"] = body
        page["version"] += 1

    def by_key(self, key: str) -> dict:
        (page,) = [
            p
            for p in self.pages.values()
            if p["props"].get("ai-dlc", {}).get("value", {}).get("key") == key
        ]
        return page

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        prefix = f"/ex/confluence/{CLOUD}/wiki/"
        assert request.url.host == "api.atlassian.com" and request.url.path.startswith(prefix)
        path = request.url.path[len(prefix) :]
        query = parse_qs(urlsplit(str(request.url)).query)
        body = json.loads(request.content) if request.content else None
        if request.method in {"POST", "PUT"}:
            self.writes += 1
        if path == "api/v2/spaces":
            return httpx.Response(200, json={"results": [{"id": "99"}], "_links": {}})
        if path == "rest/api/content/search":
            label = re.search(r'label="([^"]+)"', query["cql"][0]).group(1)
            ids = [pid for pid, p in self.pages.items() if label in p["labels"]]
            return httpx.Response(200, json={"results": [{"id": i} for i in ids]})
        if path == "api/v2/pages" and request.method == "POST":
            if any(p["title"] == body["title"] for p in self.pages.values()):
                return httpx.Response(400, json={"message": "title exists " + TOKEN})
            page_id = self._id()
            self.pages[page_id] = {
                "title": body["title"],
                "parent": body["parentId"],
                "body": body["body"]["value"],
                "version": 1,
                "labels": set(),
                "props": {},
            }
            return httpx.Response(200, json={"id": page_id, "version": {"number": 1}})
        match = re.fullmatch(r"rest/api/content/(\d+)/label", path)
        if match and request.method == "DELETE":
            self.writes += 1
            self.pages[match.group(1)]["labels"].discard(query["name"][0])
            return httpx.Response(204)
        if match:
            self.pages[match.group(1)]["labels"].update(item["name"] for item in body)
            return httpx.Response(200, json={"results": []})
        match = re.fullmatch(r"api/v2/pages/(\d+)(/.*)?", path)
        assert match, path
        rest = match.group(2) or ""
        if rest == "/children":
            kids = [pid for pid, p in self.pages.items() if p["parent"] == match.group(1)]
            return httpx.Response(200, json={"results": [{"id": k} for k in kids]})
        page = self.pages.get(match.group(1))
        if page is None:
            return httpx.Response(404)
        if rest == "" and request.method == "GET":
            assert "body-format" not in query, "the provider never reads a body"
            return httpx.Response(
                200,
                json={
                    "id": match.group(1),
                    "title": page["title"],
                    "version": {"number": page["version"]},
                    "_links": {"webui": f"/spaces/ENG/pages/{match.group(1)}"},
                },
            )
        if rest == "" and request.method == "PUT":
            if body["version"]["number"] != page["version"] + 1:
                return httpx.Response(409)
            page.update(
                title=body["title"],
                parent=body["parentId"],
                body=body["body"]["value"],
                version=body["version"]["number"],
            )
            return httpx.Response(
                200, json={"id": match.group(1), "version": {"number": page["version"]}}
            )
        if rest == "/labels":
            return httpx.Response(
                200, json={"results": [{"name": n} for n in sorted(page["labels"])]}
            )
        if rest == "/properties" and request.method == "GET":
            prop = page["props"].get(query["key"][0])
            return httpx.Response(200, json={"results": [prop] if prop else []})
        if rest == "/properties" and request.method == "POST":
            page["props"][body["key"]] = {
                "id": "p" + match.group(1),
                "key": body["key"],
                "value": body["value"],
                "version": {"number": 1},
            }
            return httpx.Response(200, json=page["props"][body["key"]])
        prop_match = re.fullmatch(r"/properties/(p\d+)", rest)
        if prop_match and request.method == "PUT":
            prop = page["props"][body["key"]]
            assert body["version"]["number"] == prop["version"]["number"] + 1
            prop.update(value=body["value"], version=body["version"])
            return httpx.Response(200, json=prop)
        raise AssertionError(f"unexpected {request.method} {path}")


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=True
    ).stdout.strip()


def record(slug, kind="decision", scope="team", body=None, **changes):
    header = {
        "id": slug,
        "type": kind,
        "scope": scope,
        "status": {"decision": "accepted", "lesson": "open"}[kind],
        "date": "2026-11-12",
        "owner": "sean",
        "sources": [{"resource": "notes/2026-11-12.md"}],
        "links": [],
        "title": slug.replace("-", " ").capitalize(),
    }
    header.update(changes)
    model = knowledge_records.KnowledgeRecord.model_validate(header)
    return knowledge_records.render(model, body or f"# {slug}\n\nWhy we chose it.\n")


@pytest.fixture
def store(tmp_path):
    repo = tmp_path / "knowledge"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    (repo / "knowledge.toml").write_text(WIKI_TOML)
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "seed")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "decisions").mkdir()
    (repo / "decisions/thursday.md").write_text(record("ship-on-thursdays"))
    (repo / "lessons").mkdir()
    (repo / "lessons/splunk.md").write_text(
        record("splunk-proxy", kind="lesson", scope="project", tags=["splunk"])
    )
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "records")
    return {"repo": repo, "base": base}


def config(repo, **wiki):
    return {
        "roles": {"knowledge": "records", "wiki": "wiki"},
        "providers": {
            "records": {"kind": "git", "location": str(repo)},
            "wiki": {**WIKI, **wiki},
        },
    }


def renderer(store, fake, **wiki):
    settings = config(store["repo"], **wiki)
    registry = Registry(settings, root=store["repo"], environ={**os.environ, **ENVIRON})
    registry.register(
        "wiki",
        ConfluenceCloud(settings["providers"]["wiki"], client=fake.client(), environ=ENVIRON),
        operations=["upsert_page", "get_page_by_key", "list_children"],
    )
    return KnowledgeRender(store["repo"], settings, registry=registry)


def commit(repo, path, text):
    (repo / path).write_text(text)
    git(repo, "add", ".")
    git(repo, "commit", "-qm", f"change {path}", "--allow-empty")


# Contract


def test_wiki_is_a_role_and_knowledge_has_no_publish():
    roles = manifest()["roles"]
    assert roles["wiki"]["mandatory"] == ["upsert_page", "get_page_by_key", "list_children"]
    assert "publish" not in roles["knowledge"]["optional"]
    assert "publish" not in manifest()["operations"]
    with pytest.raises(ValueError, match="Unsupported provider operation"):
        validate_request("publish", {})
    request = validate_request(
        "upsert_page",
        {"key": "DEC-0001", "title": "T", "body": "b", "operation_id": "op"},
    )
    assert request.payload["expected_version"] is None and request.payload["parent"] is None
    with pytest.raises(ValueError):
        validate_request(
            "upsert_page", {"key": "bad key", "title": "T", "body": "b", "operation_id": "o"}
        )
    found = validate_response("get_page_by_key", {"page": None})
    assert found == {"page": None}


# Render


def test_dry_run_plans_every_upsert_and_writes_nothing(store):
    fake = FakeConfluence()
    result = renderer(store, fake).render(store["base"], dry_run=True)
    assert result["status"] == "planned" and result["writes"] == 0
    assert fake.writes == 0
    keys = [(page["key"], page["action"]) for page in result["pages"]]
    assert keys == [
        ("index-project", "create"),
        ("index-team", "create"),
        ("ship-on-thursdays", "create"),
        ("splunk-proxy", "create"),
    ]


def test_render_writes_record_pages_under_one_index_per_scope(store):
    fake = FakeConfluence()
    result = renderer(store, fake).render(store["base"])
    assert result["status"] == "rendered" and result["writes"] == 4
    index = fake.by_key("index-team")
    page = fake.by_key("ship-on-thursdays")
    index_id = next(pid for pid, p in fake.pages.items() if p is index)
    assert index["parent"] == "1000" and page["parent"] == index_id
    assert page["title"] == "ship-on-thursdays · Ship on thursdays"
    assert "Do not edit this page." in page["body"]
    assert (
        'href="https://github.com/example/knowledge/blob/main/decisions/thursday.md"'
        in page["body"]
    )
    assert "Do not edit this page." in index["body"] and "ship-on-thursdays" in index["body"]
    assert {"ai-dlc-key-ship-on-thursdays", "decision", "team", "accepted"} <= page["labels"]
    assert "splunk" in fake.by_key("splunk-proxy")["labels"]
    value = page["props"]["ai-dlc"]["value"]
    assert value["rendered_version"] == 1
    assert value["properties"]["status"] == "accepted"
    assert value["properties"]["path"] == "decisions/thursday.md"
    assert value["properties"][HASH_PROPERTY].startswith("sha256:")
    # Index pages per scope only, never per record type.
    assert {p["props"]["ai-dlc"]["value"]["key"] for p in fake.pages.values()} == {
        "index-team",
        "index-project",
        "ship-on-thursdays",
        "splunk-proxy",
    }


def test_render_twice_writes_nothing_the_second_time(store):
    fake = FakeConfluence()
    render = renderer(store, fake)
    render.render(store["base"])
    writes = fake.writes
    again = render.render(store["base"])
    assert fake.writes == writes
    assert again["status"] == "unchanged" and again["writes"] == 0
    assert {page["action"] for page in again["pages"]} == {"unchanged"}


def test_a_hand_edit_is_restored_by_the_next_render(store):
    fake = FakeConfluence()
    render = renderer(store, fake)
    render.render(store["base"])
    page_id = next(pid for pid, p in fake.pages.items() if p is fake.by_key("ship-on-thursdays"))
    rendered = fake.pages[page_id]["body"]
    fake.hand_edit(page_id)
    result = render.render(store["base"])
    actions = {page["key"]: page["action"] for page in result["pages"]}
    assert actions["ship-on-thursdays"] == "restore"
    assert actions["index-team"] == "unchanged"
    assert fake.pages[page_id]["body"] == rendered
    assert fake.pages[page_id]["version"] == 3
    assert render.render(store["base"])["writes"] == 0


def test_a_changed_record_updates_its_page_and_index(store):
    fake = FakeConfluence()
    render = renderer(store, fake)
    render.render(store["base"])
    head = git(store["repo"], "rev-parse", "HEAD")
    commit(
        store["repo"], "decisions/thursday.md", record("ship-on-thursdays", title="Ship Thursdays")
    )
    result = render.render(head)
    actions = {page["key"]: page["action"] for page in result["pages"]}
    assert actions == {
        "index-project": "unchanged",
        "index-team": "update",
        "ship-on-thursdays": "update",
    }
    assert fake.by_key("ship-on-thursdays")["title"] == "ship-on-thursdays · Ship Thursdays"


def test_a_status_change_drops_the_old_status_label(store):
    fake = FakeConfluence()
    render = renderer(store, fake)
    render.render(store["base"])
    page = fake.by_key("splunk-proxy")
    assert "open" in page["labels"]
    page["labels"].add("added-by-hand")
    head = git(store["repo"], "rev-parse", "HEAD")
    lesson = record(
        "splunk-proxy", kind="lesson", scope="project", tags=["splunk"], status="codified"
    )
    commit(store["repo"], "lessons/splunk.md", lesson)
    render.render(head)
    labels = fake.by_key("splunk-proxy")["labels"]
    assert "codified" in labels and "open" not in labels
    assert {"splunk", "added-by-hand", "ai-dlc-key-splunk-proxy"} <= labels
    assert render.render(head)["writes"] == 0


def test_a_deleted_record_is_marked_removed_never_left_live(store):
    fake = FakeConfluence()
    render = renderer(store, fake)
    render.render(store["base"])
    head = git(store["repo"], "rev-parse", "HEAD")
    git(store["repo"], "rm", "-q", "decisions/thursday.md")
    git(store["repo"], "commit", "-qm", "retract")
    writes = fake.writes
    planned = render.render(head, dry_run=True)
    assert fake.writes == writes
    actions = {page["key"]: page["action"] for page in planned["pages"]}
    assert actions == {
        "index-project": "unchanged",
        "ship-on-thursdays": "remove",
        "index-team": "remove",
    }
    result = render.render(head)
    assert result["removed"] == ["index-team", "ship-on-thursdays"]
    assert result["orphaned"] == ["decisions/thursday.md"]
    page = fake.by_key("ship-on-thursdays")
    assert page["title"] == "Removed: ship-on-thursdays · Ship on thursdays"
    assert "Removed." in page["body"] and "Why we chose it" not in page["body"]
    assert "decisions/thursday.md" not in page["body"]
    assert page["labels"] == {"ai-dlc-removed", "ai-dlc-key-ship-on-thursdays"}
    assert page["props"]["ai-dlc"]["value"]["properties"]["removed"] == "true"
    assert fake.by_key("index-team")["title"].startswith("Removed: ")
    # Removal is idempotent, and only gone records are removed.
    again = render.render(head)
    assert again["writes"] == 0
    assert not fake.by_key("splunk-proxy")["title"].startswith("Removed")
    # A record that comes back is live again.
    (store["repo"] / "decisions").mkdir(exist_ok=True)
    commit(store["repo"], "decisions/thursday.md", record("ship-on-thursdays"))
    render.render(head)
    back = fake.by_key("ship-on-thursdays")
    assert back["title"] == "ship-on-thursdays · Ship on thursdays"
    assert "ai-dlc-removed" not in back["labels"]


def test_a_customer_record_stays_out_of_a_wiki_not_declared_for_it(store):
    commit(
        store["repo"],
        "lessons/customer.md",
        record("client-gotcha", kind="lesson", scope="project", boundary="customer"),
    )
    fake = FakeConfluence()
    result = renderer(store, fake).render(store["base"])
    assert {"key": "client-gotcha", "reason": "boundary: customer"} in result["skipped"]
    assert "client-gotcha" not in json.dumps([p["body"] for p in fake.pages.values()])

    toml = store["repo"] / "knowledge.toml"
    commit(store["repo"], "knowledge.toml", toml.read_text() + 'boundary = "customer"\n')
    renderer(store, fake).render(store["base"])
    assert fake.by_key("client-gotcha")


@pytest.mark.parametrize(
    ("toml", "wiki", "reason"),
    [
        ("[format]\nversion = 1\n", {}, "no wiki target"),
        (WIKI_TOML, {"site_url": "https://home.atlassian.net"}, "site mismatch"),
        (WIKI_TOML.replace("example.atlassian.net", "https://x"), {}, "bare atlassian.net"),
    ],
)
def test_render_refuses_before_any_request(store, toml, wiki, reason):
    commit(store["repo"], "knowledge.toml", toml)
    fake = FakeConfluence()
    result = renderer(store, fake, **wiki).render(store["base"])
    assert result["status"] == "refused" and reason in result["reason"]
    assert fake.requests == []


# Provider


def provider(fake, **changes):
    return ConfluenceCloud({**WIKI, **changes}, client=fake.client(), environ=ENVIRON)


def test_upsert_refuses_a_stale_expected_version(store):
    fake = FakeConfluence()
    wiki = provider(fake)
    page = wiki.upsert_page("k-1", "One", "body", operation_id="o")
    assert page["version"] == 1 and page["rendered_version"] == 1
    with pytest.raises(ConfluenceRefusal, match="version conflict"):
        wiki.upsert_page("k-1", "One", "body", operation_id="o")
    with pytest.raises(ConfluenceRefusal, match="version conflict"):
        wiki.upsert_page("k-2", "Two", "body", expected_version=3, operation_id="o")
    fake.hand_edit(page["page_id"])
    with pytest.raises(ConfluenceRefusal, match="version conflict"):
        wiki.upsert_page("k-1", "One", "body", expected_version=1, operation_id="o")
    found = wiki.get_page_by_key("k-1")["page"]
    assert found["version"] == 2 and found["rendered_version"] == 1
    assert "body" not in found
    children = wiki.list_children(None)["pages"]
    assert [child["key"] for child in children] == ["k-1"]


def test_provider_errors_are_fixed_and_never_carry_credentials():
    fake = FakeConfluence()
    with pytest.raises(ConfluenceRefusal, match="not populated"):
        ConfluenceCloud(WIKI, client=fake.client(), environ={})
    for bad in (
        {"site_url": "https://example.atlassian.net/wiki"},
        {"cloud_id": "nope"},
        {"parent_id": "root"},
        {"auth_mode": "password"},
        {"token_env": "not a name"},
    ):
        with pytest.raises(ConfluenceRefusal):
            provider(fake, **bad)
    wiki = provider(fake)
    wiki.upsert_page("k-1", "Same", "body", operation_id="o")
    with pytest.raises(Exception) as caught:
        wiki.upsert_page("k-2", "Same", "body", operation_id="o")
    assert TOKEN not in str(caught.value) and "HTTP 400" in str(caught.value)
    assert isinstance(caught.value, (RefusedError, confluence_cloud.ConfluenceUncertain))


def test_storage_format_covers_the_rendered_markdown():
    out = storage(
        "> **Do not edit.** See [a](https://x/y?a=1&b=2).\n\n"
        "| A | B |\n| --- | --- |\n| 1 | `x<y` |\n\n## Links\n\n- one\n- two\n\n"
        "```python\nprint('<hi>')\n```\n"
    )
    assert (
        '<blockquote><p><strong>Do not edit.</strong> See <a href="https://x/y?a=1&amp;b=2">a</a>.</p></blockquote>'
        in out
    )
    assert "<tr><th>A</th><th>B</th></tr><tr><td>1</td><td><code>x&lt;y</code></td></tr>" in out
    assert "<h2>Links</h2><ul><li>one</li><li>two</li></ul>" in out
    assert "<![CDATA[print('<hi>')]]>" in out


# Entry points


def test_cli_dry_run_through_the_project_configuration(store, tmp_path, monkeypatch):
    fake = FakeConfluence()
    real = httpx.Client
    monkeypatch.setattr(
        confluence_cloud.httpx,
        "Client",
        lambda **kwargs: real(transport=httpx.MockTransport(fake.handle)),
    )
    monkeypatch.setenv("CONFLUENCE_TOKEN", TOKEN)
    root = tmp_path / "project"
    root.mkdir()
    wiki = "\n".join(f'{k} = "{v}"' for k, v in WIKI.items())
    (root / "ai-dlc.toml").write_text(
        'schema = 4\n[roles]\nknowledge = "records"\nwiki = "wiki"\n'
        f'[providers.records]\nkind = "git"\nlocation = "{store["repo"]}"\n'
        f"[providers.wiki]\n{wiki}\n"
    )
    runner = CliRunner()
    arguments = ["knowledge", "render", "--root", str(root), "--changed-since", store["base"]]
    planned = runner.invoke(app, [*arguments, "--dry-run"])
    assert planned.exit_code == 0, planned.output
    assert json.loads(planned.output)["status"] == "planned" and fake.writes == 0
    written = runner.invoke(app, arguments)
    assert written.exit_code == 0, written.output
    assert json.loads(written.output)["writes"] == 4
    refused = runner.invoke(
        app, ["knowledge", "render", "--root", str(root), "--changed-since", "nope"]
    )
    assert refused.exit_code == 1


def test_mcp_exposes_render_and_no_publish_commands(tmp_path):
    import asyncio

    from ai_dlc.mcp_server import make_server

    names = {tool.name for tool in asyncio.run(make_server(tmp_path).list_tools())}
    assert "knowledge_render" in names
    commands = CliRunner().invoke(app, ["knowledge", "--help"]).output
    assert "render" in commands and "publish-plan" not in commands


def test_the_retired_publish_path_is_gone():
    root = Path(__file__).resolve().parents[1]
    assert not (root / "agents/skills/kb-publish").exists()
    assert not (root / "contracts/publish.request.schema.json").exists()
