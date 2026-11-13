"""The git provider for the knowledge role: read, search, list changes, propose by PR.

A local bare repository stands in for the remote and a recording ``gh`` stands in
for GitHub. Nothing here reaches a live service.
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.contracts import manifest, validate_request, validate_response
from ai_dlc.documentation import knowledge_records, record_index
from ai_dlc.documentation.knowledge_publish import source_sha256
from ai_dlc.documentation.knowledge_service import KnowledgeRecords
from ai_dlc.providers import Registry

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/knowledge_records"
REPOSITORY = "example/knowledge"
PR_URL = f"https://github.com/{REPOSITORY}/pull/3"


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=True
    ).stdout.strip()


def record(slug="ship-on-thursdays", kind="decision", **changes):
    header = {
        "id": slug,
        "type": kind,
        "scope": "team",
        "status": {"decision": "proposed", "lesson": "open", "source": "raw"}[kind],
        "date": "2026-11-12",
        "owner": "sean",
        "sources": [{"resource": "notes/2026-11-12.md"}],
        "links": [],
    }
    if kind == "source":
        header.update(
            schema_version=1,
            revision="1",
            provider="zoom",
            title="Call",
            observed_at="2026-11-12T15:00:00-05:00",
        )
    header.update(changes)
    model = knowledge_records.KnowledgeRecord.model_validate(header)
    return knowledge_records.render(model, f"# {slug}\n")


@pytest.fixture
def store(tmp_path, monkeypatch):
    """A bare remote seeded with a pinned record tree, a clone, and a recording gh."""
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", "--quiet", str(remote), str(seed))
    git(seed, "config", "user.email", "test@example.invalid")
    git(seed, "config", "user.name", "Test")
    git(seed, "switch", "-c", "main")
    (seed / "knowledge.toml").write_text("[format]\nversion = 1\n")
    (seed / "README.md").write_text("# Knowledge\n")
    for path in sorted((FIXTURES / "1-meeting").glob("*.md")):
        (seed / "records").mkdir(exist_ok=True)
        (seed / "records" / path.name).write_text(path.read_text())
    (seed / "records/accepted.md").write_text(record("keep-main-green", status="accepted"))
    git(seed, "add", ".")
    git(seed, "commit", "-m", "seed")
    git(seed, "push", "--quiet", "origin", "main")
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "--quiet", str(remote), str(clone))

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh.log"
    script = bin_dir / "gh"
    script.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{log}"\necho "{PR_URL}"\n')
    script.chmod(0o755)
    environ = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path / "home"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    monkeypatch.setenv("PATH", environ["PATH"])
    return {"remote": remote, "clone": clone, "log": log, "environ": environ, "tmp": tmp_path}


def registry(store, location=None, **settings):
    config = {
        "roles": {"knowledge": "team", "scm": "github"},
        "providers": {
            "team": {"kind": "git", "repository": REPOSITORY, **settings},
        },
    }
    environ = {**store["environ"], "KNOWLEDGE_REPO": str(location or store["clone"])}
    return Registry(config, root=store["tmp"], environ=environ)


def service(store, **settings):
    reg = registry(store, **settings)
    return KnowledgeRecords(store["tmp"], reg.config, registry=reg)


def remote_files(store, ref):
    return git(store["remote"], "ls-tree", "-r", "--name-only", ref).splitlines()


# Contract


def test_knowledge_role_reads_records_and_proposes_optionally():
    roles = manifest()["roles"]
    assert roles["knowledge"] == {
        "mandatory": ["get", "search"],
        "optional": ["append", "list_changed", "propose", "publish"],
    }
    with pytest.raises(ValueError):
        validate_request("propose", {"records": [], "branch": "b", "title": "t"})
    with pytest.raises(ValueError):
        validate_request("get", {"id": ""})
    published = json.loads((ROOT / "contracts/propose.request.schema.json").read_text())
    assert published["properties"]["records"]["minItems"] == 1


def obsidian(tmp_path):
    vault = tmp_path / "vault"
    (vault / "records").mkdir(parents=True)
    for path in sorted((FIXTURES / "1-meeting").glob("*.md")):
        (vault / "records" / path.name).write_text(path.read_text())
    (vault / "learnings").mkdir()
    (vault / "learnings/old.md").write_text("---\nkind: note\n---\nlegacy\n")
    config = {"roles": {"knowledge": "obsidian"}, "paths": {"vault": str(vault)}}
    return Registry(config, root=tmp_path, environ={}), "obsidian"


@pytest.mark.parametrize("kind", ["git", "obsidian"])
def test_both_providers_meet_the_read_contract(kind, store):
    reg, provider_id = (registry(store), "team") if kind == "git" else obsidian(store["tmp"])
    found = reg.invoke(provider_id, "get", {"id": "SRC-0001"})
    assert found["path"] == "records/source.md"
    assert found["header"]["type"] == "source"
    assert "Speaker 1" in found["body"]
    decisions = reg.invoke(provider_id, "search", {"type": "decision"})
    seeded = ["keep-main-green"] if kind == "git" else []
    assert sorted(item["id"] for item in decisions["items"]) == [
        *seeded,
        "pin-harness-by-digest",
        "releases-ship-on-thursdays",
    ]
    assert validate_response("search", decisions) == decisions
    with pytest.raises(LookupError):
        reg.invoke(provider_id, "get", {"id": "DEC-9999"})


# Reading


def test_search_filters_on_header_and_reads_bodies_only_for_text(store, monkeypatch):
    clone = store["clone"]
    (clone / "records/tagged.md").write_text(
        record("tagged-lesson", "lesson", tags=["splunk"], label="internal")
    )
    provider = registry(store).get("team")
    assert [i["id"] for i in provider.search(labels=["splunk", "internal"])["items"]] == [
        "tagged-lesson"
    ]
    assert provider.search(labels=["splunk", "other"])["items"] == []
    assert [i["id"] for i in provider.search(scope="team", status="open")["items"]] == [
        "tagged-lesson"
    ]

    def no_bodies(self, *args, **kwargs):
        raise AssertionError(f"read a whole file: {self}")

    monkeypatch.setattr(Path, "read_text", no_bodies)
    assert len(provider.search()["items"]) == 6
    with pytest.raises(AssertionError, match="whole file"):
        provider.search(text="harness")
    monkeypatch.undo()
    found = provider.search(text="PIN THE HARNESS")["items"]
    assert sorted(i["id"] for i in found) == ["SRC-0001", "pin-harness-by-digest"]


def test_search_returns_customer_records_only_to_their_project(store):
    clone = store["clone"]
    alpha = clone / "projects/alpha"
    alpha.mkdir(parents=True)
    customer = {"scope": "project", "boundary": "customer", "tags": ["splunk"]}
    (alpha / "gotcha.md").write_text(record("alpha-gotcha", "lesson", **customer))
    (clone / "projects/beta").mkdir()
    (clone / "projects/beta/broken.md").write_text("---\nid: x\ntype: lesson\n---\n")
    (clone / "records/tagged.md").write_text(record("team-lesson", "lesson", tags=["splunk"]))
    provider = registry(store).get("team")

    def found(**filters):
        result = provider.search(labels=["splunk"], **filters)
        return [item["id"] for item in result["items"]], [i["path"] for i in result["invalid"]]

    assert found() == (["team-lesson"], [])
    assert found(text="alpha-gotcha") == ([], [])
    assert found(project="beta") == (["team-lesson"], ["projects/beta/broken.md"])
    assert found(project="alpha") == (["alpha-gotcha", "team-lesson"], [])


def test_invalid_records_are_reported_not_returned(store):
    (store["clone"] / "records/broken.md").write_text("---\nid: x\ntype: decision\n---\n")
    result = registry(store).get("team").search()
    assert [entry["path"] for entry in result["invalid"]] == ["records/broken.md"]
    assert "records/broken.md" not in [item["path"] for item in result["items"]]


def test_a_url_location_is_cloned_into_the_cache_and_refreshed(store):
    url = store["remote"].as_uri()
    provider = registry(store, location=url).get("team")
    assert provider.get("pin-harness-by-digest")["header"]["domain"] == "harness"
    clone = store["clone"]
    (clone / "records/new.md").write_text(record("new-decision"))
    git(clone, "add", ".")
    git(clone, "-c", "user.email=t@example.invalid", "-c", "user.name=T", "commit", "-m", "add")
    git(clone, "push", "--quiet", "origin", "main")
    assert provider.get("new-decision")["path"] == "records/new.md"
    assert str(provider.repository_root()).startswith(store["environ"]["XDG_CACHE_HOME"])


def test_list_changed_names_added_modified_and_deleted_records(store):
    clone = store["clone"]
    since = git(clone, "rev-parse", "HEAD")
    (clone / "records/new.md").write_text(record("new-decision"))
    (clone / "records/action.md").unlink()
    text = (clone / "records/source.md").read_text().replace("Speaker 2", "Speaker Two")
    (clone / "records/source.md").write_text(text)
    git(clone, "add", "-A")
    git(clone, "-c", "user.email=t@example.invalid", "-c", "user.name=T", "commit", "-m", "x")
    result = registry(store).invoke("team", "list_changed", {"since": since})
    assert result["since"] == since
    assert sorted((c["path"], c["change"], c.get("id")) for c in result["changed"]) == [
        ("records/action.md", "deleted", None),
        ("records/new.md", "added", "new-decision"),
        ("records/source.md", "modified", "SRC-0001"),
    ]
    assert service(store).list_changed("no-such-ref")["status"] == "refused"


# Proposing


def test_propose_pushes_exactly_the_records_and_opens_a_draft_pr(store):
    main_before = git(store["remote"], "rev-parse", "main")
    records = [
        {"path": "records/ship.md", "text": record()},
        {"path": "lessons/proxy.md", "text": record("proxy-ca", "lesson")},
    ]
    result = service(store).propose(records, "knowledge/ship", "Propose two records", "Why")

    assert result["status"] == "proposed"
    assert result["pull_request"] == {"url": PR_URL, "number": 3}
    assert result["files"] == ["lessons/proxy.md", "records/ship.md"]
    changed = git(store["remote"], "diff", "--name-only", "main", "knowledge/ship")
    assert sorted(changed.splitlines()) == ["lessons/proxy.md", "records/ship.md"]
    assert git(store["remote"], "rev-parse", "knowledge/ship") == result["commit"]
    assert git(store["remote"], "rev-parse", "main") == main_before
    arguments = store["log"].read_text().splitlines()
    assert arguments[:8] == [
        "pr", "create", "--repo", REPOSITORY, "--base", "main", "--head", "knowledge/ship",
    ]  # fmt: skip
    assert arguments[8:10] == ["--title", "Propose two records"]
    assert arguments[-1] == "--draft"
    clone = store["clone"]
    assert git(clone, "worktree", "list").count("\n") == 0
    assert "knowledge/ship" not in git(clone, "branch", "--list")
    assert git(clone, "status", "--porcelain") == ""


@pytest.mark.parametrize(
    ("records", "branch", "reason"),
    [
        ([{"path": "records/bad.md", "text": "---\nid: x\ntype: decision\n---\n"}], "k/b", "check"),
        ([{"path": "records/bad.md", "text": "no frontmatter"}], "k/b", "frontmatter"),
        ([{"path": "records/ok.md", "text": record()}], "main", "new branch"),
        ([{"path": "../escape.md", "text": record()}], "k/b", "escapes"),
        ([{"path": "records/ok.txt", "text": record()}], "k/b", ".md"),
        (
            [{"path": "records/other.md", "text": record("pin-harness-by-digest")}],
            "k/b",
            "is used by records/decision-pin-harness.md",
        ),
    ],
)
def test_a_record_that_fails_the_check_is_refused_before_any_push(store, records, branch, reason):
    main_before = git(store["remote"], "rev-parse", "main")
    result = service(store).propose(records, branch, "Title")
    assert result["status"] in {"refused", "failed"} or "error" in result
    assert reason in result.get("reason", "")
    assert git(store["remote"], "branch", "--list") == "* main"
    assert git(store["remote"], "rev-parse", "main") == main_before
    assert not store["log"].exists()


def accepted_edit():
    text = record("keep-main-green", status="accepted").replace("# keep-main-green", "# edited")
    return [{"path": "records/accepted.md", "text": text}]


@pytest.mark.parametrize(
    ("records", "reason"),
    [
        (
            [
                {
                    "path": "records/linked.md",
                    "text": record(
                        "linked", links=[{"type": "implements", "target": "no-such-record"}]
                    ),
                }
            ],
            "no-such-record",
        ),
        (
            [
                {
                    "path": "records/replaces.md",
                    "text": record(
                        "replaces",
                        status="accepted",
                        links=[{"type": "supersedes", "target": "keep-main-green"}],
                    ),
                }
            ],
            "supersed",
        ),
        (accepted_edit(), "accepted"),
    ],
    ids=["broken-link", "bad-supersession", "edited-accepted-decision"],
)
def test_propose_runs_knowledge_check_against_the_base_before_pushing(store, records, reason):
    main_before = git(store["remote"], "rev-parse", "main")
    result = service(store).propose(records, "k/checked", "Title")
    assert result["status"] == "refused", result
    assert result["reason"].startswith("knowledge check failed")
    assert reason in result["reason"]
    assert git(store["remote"], "branch", "--list") == "* main"
    assert git(store["remote"], "rev-parse", "main") == main_before
    assert not store["log"].exists()
    clone = store["clone"]
    assert "k/checked" not in git(clone, "branch", "--list")
    assert git(clone, "worktree", "list").count("\n") == 0


def test_raised_refusals_reach_the_cli_as_failures(store):
    reg = registry(store)
    with pytest.raises(ValueError, match="escapes"):
        reg.invoke(
            "team",
            "propose",
            {"records": [{"path": "../x.md", "text": record()}], "branch": "k/b", "title": "t"},
        )


def test_propose_refuses_a_tree_without_a_format_pin(store):
    clone = store["clone"]
    git(clone, "rm", "--quiet", "knowledge.toml")
    git(clone, "-c", "user.email=t@example.invalid", "-c", "user.name=T", "commit", "-m", "x")
    git(clone, "push", "--quiet", "origin", "main")
    result = service(store).propose([{"path": "r/a.md", "text": record()}], "k/b", "t")
    assert result["status"] == "refused"
    assert "knowledge.toml" in result["reason"]
    assert not store["log"].exists()


def test_propose_refuses_an_existing_remote_branch(store):
    git(store["clone"], "push", "--quiet", "origin", "main:refs/heads/k/b")
    result = service(store).propose([{"path": "r/a.md", "text": record()}], "k/b", "t")
    assert result["status"] == "refused"
    assert "already exists" in result["reason"]


# Duplicates (carried forward from the capture dedupe of ADR 0003)


SOURCE_TEXT = b"WEBVTT\r\n\r\n00:00.000 --> 00:01.000\r\nAda: ship it\r\n"


def hashed_source(slug, digest, **changes):
    return record(slug, "source", sources=[{"resource": "x.vtt", "hash": f"sha256:{digest}"}])


def test_source_digest_ignores_line_endings_and_finds_captured_records(store, tmp_path):
    digest = source_sha256(SOURCE_TEXT)
    assert digest == hashlib.sha256(SOURCE_TEXT.replace(b"\r\n", b"\n")).hexdigest()
    transcript = tmp_path / "roadmap.vtt"
    transcript.write_bytes(SOURCE_TEXT)
    records = service(store)
    assert records.captured(transcript) == {"status": "new", "sha256": digest, "records": []}
    (store["clone"] / "inbox").mkdir()
    (store["clone"] / "inbox/roadmap.md").write_text(hashed_source("roadmap-call", digest))
    (store["clone"] / "inbox/broken.md").write_text("---\n- not a mapping\n---\n")
    unix = tmp_path / "roadmap-unix.vtt"
    unix.write_bytes(SOURCE_TEXT.replace(b"\r\n", b"\n"))
    result = records.captured(unix)
    assert result["status"] == "captured"
    assert result["records"] == ["inbox/roadmap.md"]


def test_propose_refuses_a_source_captured_before(store):
    digest = source_sha256(SOURCE_TEXT)
    first = service(store).propose(
        [{"path": "inbox/a.md", "text": hashed_source("call-a", digest)}], "k/a", "t"
    )
    assert first["status"] == "proposed"
    clone = store["clone"]
    (clone / "inbox").mkdir()
    (clone / "inbox/a.md").write_text(hashed_source("call-a", digest))
    git(clone, "add", ".")
    git(clone, "-c", "user.email=t@example.invalid", "-c", "user.name=T", "commit", "-m", "x")
    git(clone, "push", "--quiet", "origin", "main")
    again = service(store).propose(
        [{"path": "inbox/b.md", "text": hashed_source("call-b", digest)}], "k/b", "t"
    )
    assert again["status"] == "refused"
    assert "duplicates inbox/a.md" in again["reason"]
    assert "derived_from" in again["reason"]


def test_two_decisions_from_one_source_are_not_duplicates_unless_titles_match():
    def entry(path, slug, title):
        text = record(
            slug,
            sources=[{"id": "SRC-0001", "resource": "s.md", "hash": "sha256:" + "a" * 64}],
            links=[{"type": "derived_from", "target": "SRC-0001"}],
            title=title,
        )
        return {"path": path, "record": knowledge_records.parse(text)[0]}

    existing = [entry("a.md", "first", "Ship on Thursdays")]
    assert record_index.duplicates(existing, [entry("b.md", "second", "Pin by digest")]) == []
    found = record_index.duplicates(existing, [entry("c.md", "third", "Ship on Thursdays")])
    assert found and found[0].startswith("c.md: duplicates a.md")


# CLI


def project(store, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(
        'schema = 4\n[roles]\nknowledge = "team"\nscm = "github"\n'
        f'[providers.team]\nkind = "git"\nrepository = "{REPOSITORY}"\n'
    )
    return root


def test_cli_reads_and_proposes_through_the_shared_service(store, tmp_path, monkeypatch):
    for key, value in store["environ"].items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("KNOWLEDGE_REPO", str(store["clone"]))
    root = project(store, tmp_path)
    runner = CliRunner()
    got = runner.invoke(app, ["knowledge", "records", "get", "SRC-0001", "--root", str(root)])
    assert got.exit_code == 0, got.output
    assert json.loads(got.output)["status"] == "ok"
    missing = runner.invoke(app, ["knowledge", "records", "get", "nope", "--root", str(root)])
    assert missing.exit_code == 1
    found = runner.invoke(
        app, ["knowledge", "records", "search", "--type", "action", "--root", str(root)]
    )
    assert [i["id"] for i in json.loads(found.output)["items"]] == ["share-release-notes"]

    draft = tmp_path / "ship.md"
    draft.write_text(record())
    bad = tmp_path / "bad.md"
    bad.write_text("---\nid: x\n---\n")
    arguments = ["knowledge", "records", "propose", "--root", str(root), "--branch", "k/c"]
    refused = runner.invoke(app, [*arguments, "--title", "t", str(bad)])
    assert refused.exit_code == 1
    assert json.loads(refused.output)["status"] == "refused"
    proposed = runner.invoke(
        app, [*arguments, "--title", "t", "--path", "records/ship.md", str(draft)]
    )
    assert proposed.exit_code == 0, proposed.output
    assert json.loads(proposed.output)["pull_request"]["url"] == PR_URL

    transcript = tmp_path / "call.vtt"
    transcript.write_bytes(SOURCE_TEXT)
    new = runner.invoke(
        app, ["knowledge", "records", "captured", str(transcript), "--root", str(root)]
    )
    assert new.exit_code == 0, new.output
