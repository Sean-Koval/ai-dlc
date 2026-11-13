"""The MCP surface an agent with only ``ai-dlc mcp serve`` needs: work, knowledge, tracker.

Tools are driven through a real MCP client session. Providers are fakes: a recording
``gh`` stands in for GitHub and an in-memory tracker for Jira. Nothing is live.
"""

import asyncio
import json
import os
import subprocess

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from test_git_knowledge import PR_URL, REPOSITORY, record, store  # noqa: F401

from ai_dlc.mcp_server import make_server
from ai_dlc.providers import Registry

TOOLS = {
    "doctor",
    "knowledge_append",
    "knowledge_check",
    "knowledge_find",
    "knowledge_get",
    "knowledge_index",
    "knowledge_note",
    "knowledge_number_plan",
    "knowledge_propose",
    "knowledge_render",
    "knowledge_search",
    "knowledge_template",
    "project_docs_check",
    "project_docs_disposition",
    "project_docs_gate",
    "project_docs_impact",
    "project_docs_inventory",
    "project_docs_read",
    "project_docs_record",
    "project_docs_review",
    "project_docs_review_check",
    "project_docs_search",
    "project_vault_mount_preview",
    "project_workspace_check",
    "project_workspace_preview",
    "tracker_create",
    "tracker_get",
    "tracker_update",
    "work_archive",
    "work_context",
    "work_finish",
    "work_link",
    "work_new",
    "work_pr",
    "work_publish",
    "work_review",
    "work_start",
    "work_status",
}


def call(server, *calls):
    """Run tool calls in order through one client session; return their JSON results."""

    async def run():
        results = []
        async with create_connected_server_and_client_session(server._mcp_server) as client:
            for name, arguments in calls:
                result = await client.call_tool(name, arguments)
                text = result.content[0].text if result.content else ""
                results.append(text if result.isError else json.loads(text))
        return results

    return asyncio.run(run())


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=True
    ).stdout.strip()


class Tracker:
    """An in-memory tracker: create once by correlation, read, transition, update."""

    def __init__(self, operations=("update",)):
        self.items = {}
        self.payloads = []
        self.operations = list(operations)

    def invoke(self, operation, payload):
        self.payloads.append((operation, payload))
        if operation == "capabilities":
            return {
                "schema": 1,
                "lifecycle": {"in_progress": True, "closed": True},
                "optional_operations": self.operations,
            }
        if operation == "find":
            return {
                "items": [
                    i for i in self.items.values() if i["correlation"] == payload["correlation"]
                ]
            }
        if operation == "create":
            found = self.invoke("find", {"correlation": payload["correlation"]})["items"]
            if found:
                return found[0]
            number = str(len(self.items) + 1)
            self.items[number] = {
                "id": number,
                "url": f"https://tracker.example/{number}",
                "state": "open",
                "correlation": payload["correlation"],
                "labels": list(payload.get("labels", [])),
            }
            return self.items[number]
        item = self.items[payload["reference"]]
        if operation == "transition":
            item["state"] = payload["state"]
        if operation == "update" and payload.get("labels") is not None:
            item["labels"] = list(payload["labels"])
        return item


class Providers(Registry):
    """The project's real providers, with the tracker replaced by a fake."""

    def __init__(self, config, root, tracker):
        super().__init__(config, root=root)
        self.register("tickets", tracker, operations=["capabilities"])


def project(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(
        'schema = 4\n[roles]\ntracker = "tickets"\nscm = "github"\n'
        '[scm]\nrepository = "a/b"\ntarget_branch = "main"\n'
    )
    (root / ".gitignore").write_text("state/\n")
    git(tmp_path, "init", "-b", "main", str(root))
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    git(root, "add", ".")
    git(root, "commit", "-m", "initial")
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", str(remote))
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "--quiet", "-u", "origin", "main")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh.log"
    script = bin_dir / "gh"
    script.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$@" > "{log}"\necho "https://github.com/a/b/pull/12"\n'
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("AI_DLC_AUTHOR", "reviewer")
    return root, log


def server_for(root, tracker):
    from ai_dlc.cli import config_for

    return make_server(root, registry=Providers(config_for(root), root, tracker))


# The tool list


def test_the_tool_list_is_complete_and_has_no_generic_provider_mutation(tmp_path):
    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    server = make_server(tmp_path)

    names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert names == TOOLS, "update TOOLS when a tool is added or removed"
    assert not names & {"provider_invoke", "tracker_transition", "tracker_complete"}


def test_every_tool_argument_is_typed(tmp_path):
    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    new = {"work_new", "work_pr", "work_archive", "tracker_create", "tracker_update"}
    new |= {"tracker_get", "knowledge_get", "knowledge_search", "knowledge_propose"}
    for tool in asyncio.run(make_server(tmp_path).list_tools()):
        if tool.name not in new | {"knowledge_template"}:
            continue
        for name, schema in tool.inputSchema["properties"].items():
            kinds = [schema, *schema.get("anyOf", [])]
            assert any("type" in kind or "$ref" in kind for kind in kinds), (tool.name, name)
            assert not any(kind.get("type") == "object" for kind in kinds), (tool.name, name)


# Work


def test_work_new_then_work_pr_through_the_mcp_client(tmp_path, monkeypatch):
    root, log = project(tmp_path, monkeypatch)
    tracker = Tracker()
    server = server_for(root, tracker)

    new, reviewed, started = call(
        server,
        (
            "work_new",
            {
                "work_id": "one",
                "title": "One",
                "scope": "small",
                "requires_spec": False,
                "spec_reason": "No behaviour change",
                "acceptance": ["Tests pass"],
            },
        ),
        ("work_review", {"work_id": "one"}),
        ("work_start", {"work_id": "one"}),
    )
    assert new["status"] == "created"
    assert {"tracker": "tickets", "scm": "github"}.items() <= new["work"]["providers"].items()
    assert reviewed["status"] == "reviewed", reviewed
    assert started["status"] == "started", started
    git(root, "push", "--quiet", "-u", "origin", started["branch"])

    (opened,) = call(server, ("work_pr", {"work_id": "one"}))

    assert opened["status"] == "created", opened
    assert opened["pr"]["url"] == "https://github.com/a/b/pull/12"
    arguments = log.read_text().splitlines()
    assert arguments[:8] == [
        "pr", "create", "--repo", "a/b", "--base", "main", "--head", started["branch"],
    ]  # fmt: skip
    assert git(root, "log", "-1", "--format=%s") == "chore(work): link pr for one"
    (again,) = call(server, ("work_pr", {"work_id": "one"}))
    assert again["status"] == "linked"


def test_work_archive_refuses_without_an_active_change(tmp_path, monkeypatch):
    root, _ = project(tmp_path, monkeypatch)
    server = server_for(root, Tracker())
    call(
        server,
        (
            "work_new",
            {
                "work_id": "one",
                "title": "One",
                "scope": "small",
                "requires_spec": False,
                "spec_reason": "No behaviour change",
                "acceptance": ["Tests pass"],
            },
        ),
        ("work_review", {"work_id": "one"}),
    )

    (refused,) = call(server, ("work_archive", {"work_id": "one"}))

    assert "active openspec/changes/<id>" in refused


# Knowledge


def knowledge_project(store, tmp_path, monkeypatch):  # noqa: F811
    for key, value in store["environ"].items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("KNOWLEDGE_REPO", str(store["clone"]))
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(
        'schema = 4\n[roles]\nknowledge = "team"\nscm = "github"\n'
        f'[providers.team]\nkind = "git"\nrepository = "{REPOSITORY}"\n'
    )
    return make_server(root)


def test_knowledge_propose_pushes_a_branch_and_opens_a_draft_pr(store, tmp_path, monkeypatch):  # noqa: F811
    server = knowledge_project(store, tmp_path, monkeypatch)
    records = [{"path": "records/ship.md", "text": record()}]

    (proposed,) = call(
        server,
        ("knowledge_propose", {"records": records, "branch": "k/ship", "title": "Ship"}),
    )

    assert proposed["status"] == "proposed", proposed
    assert proposed["pull_request"]["url"] == PR_URL
    changed = git(store["remote"], "diff", "--name-only", "main", "k/ship")
    assert changed.splitlines() == ["records/ship.md"]
    assert store["log"].read_text().splitlines()[-1] == "--draft"


def test_knowledge_get_and_search_respect_the_customer_boundary(store, tmp_path, monkeypatch):  # noqa: F811
    server = knowledge_project(store, tmp_path, monkeypatch)

    found, got, missing = call(
        server,
        ("knowledge_search", {"type": "action"}),
        ("knowledge_get", {"id": "SRC-0001"}),
        ("knowledge_get", {"id": "nope", "project": "acme"}),
    )

    assert found["status"] == "ok"
    assert [item["id"] for item in found["items"]] == ["share-release-notes"]
    assert got["status"] == "ok"
    assert missing["status"] != "ok"


def test_knowledge_template_lists_types_and_returns_one(tmp_path):
    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    server = make_server(tmp_path)

    listed, decision, unknown = call(
        server,
        ("knowledge_template", {}),
        ("knowledge_template", {"type": "decision"}),
        ("knowledge_template", {"type": "memo"}),
    )

    assert "decision" in listed["types"]
    assert decision["status"] == "ok" and decision["text"].startswith("---")
    assert unknown["status"] == "refused"


# Tracker


def tracker_server(tmp_path, tracker):
    (tmp_path / "ai-dlc.toml").write_text('schema = 4\n[roles]\ntracker = "tickets"\n')
    return server_for(tmp_path, tracker)


def test_tracker_create_files_once_and_reports_exec_labels(tmp_path):
    tracker = Tracker()
    server = tracker_server(tmp_path, tracker)
    arguments = {"title": "Plan step", "body": "Do it", "labels": ["exec:pair", "repo:ai-dlc"]}

    first, second = call(server, ("tracker_create", arguments), ("tracker_create", arguments))

    assert first["status"] == "created"
    assert first["exec_labels"] == ["exec:pair"]
    assert first["labels"] == ["exec:pair", "repo:ai-dlc"]
    assert second["item"]["id"] == first["item"]["id"]
    assert len(tracker.items) == 1


@pytest.mark.parametrize(
    "label", ["exec:agent", "EXEC:AGENT", "Exec:Agent", " exec:agent ", "lane:Agent"]
)
def test_tracker_tools_refuse_to_queue_a_ticket_for_an_agent(tmp_path, label):
    tracker = Tracker()
    server = tracker_server(tmp_path, tracker)
    tracker.invoke("create", {"title": "t", "correlation": "c", "operation_id": "o"})

    created, updated = call(
        server,
        ("tracker_create", {"title": "t", "labels": ["exec:pair", label]}),
        ("tracker_update", {"reference": "1", "labels": [label]}),
    )

    assert created["status"] == "refused"
    assert updated["status"] == "refused"
    assert "agent" in created["reason"]
    assert [op for op, _ in tracker.payloads if op in {"create", "update"}] == ["create"]


def test_tracker_update_replaces_labels_but_keeps_one_a_person_set(tmp_path):
    tracker = Tracker()
    server = tracker_server(tmp_path, tracker)
    tracker.invoke(
        "create",
        {"title": "t", "correlation": "c", "operation_id": "o", "labels": ["exec:agent", "x"]},
    )

    (updated,) = call(server, ("tracker_update", {"reference": "1", "labels": ["exec:pair"]}))

    assert updated["status"] == "updated"
    assert updated["labels"] == ["exec:pair", "exec:agent"]
    assert updated["exec_labels"] == ["exec:pair", "exec:agent"]


def test_labels_are_refused_before_writing_when_the_provider_cannot_write_them(tmp_path):
    tracker = Tracker(operations=["link"])
    server = tracker_server(tmp_path, tracker)

    labelled, plain, update = call(
        server,
        ("tracker_create", {"title": "t", "labels": ["exec:pair"]}),
        ("tracker_create", {"title": "t"}),
        ("tracker_update", {"reference": "1", "title": "u"}),
    )

    assert labelled["status"] == "refused"
    assert plain["status"] == "created" and plain["exec_labels"] == []
    assert update["status"] == "refused"
    assert [op for op, _ in tracker.payloads if op == "create"] == ["create"]
