"""Capture note kinds, source dedupe, the origin/site wall and the publish op (ADR 0003)."""

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.contracts import manifest, validate_request, validate_response
from ai_dlc.documentation import knowledge_notes, knowledge_publish

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "a" * 64
WORK_SITE = "acme.atlassian.net"
HOME_SITE = "example.atlassian.net"


def meeting(**changes):
    note = {
        "id": "meeting/2026-11-08-roadmap",
        "kind": "meeting",
        "scope": "personal",
        "label": "internal",
        "author": "agent:claude-code",
        "valid_from": "2026-11-08",
        "origin": "work",
        "lane": "ENG-12",
        "source": {"file": "Inbox/meetings/roadmap.vtt", "sha256": DIGEST},
    }
    note.update(changes)
    return {key: value for key, value in note.items() if value is not None}


def front(fields, body="# Roadmap sync\n\n## Decisions\n- Ship phase A\n"):
    return "---\n" + knowledge_notes.dump(fields) + "---\n" + body


def vault(tmp_path, origin="work", site=WORK_SITE, parent='"98765"'):
    root = tmp_path / "vault"
    (root / ".ai-dlc").mkdir(parents=True)
    lines = [f'origin = "{origin}"', f'site = "{site}"', 'space = "ENG"']
    if parent:
        lines.append(f"parent = {parent}")
    (root / ".ai-dlc/publish.toml").write_text("\n".join(lines) + "\n")
    return root


def write(root, relative, fields, body=None):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(front(fields) if body is None else front(fields, body))
    return relative


# Schema


def test_capture_kinds_validate_and_existing_kinds_need_no_origin():
    assert knowledge_notes.errors(meeting()) == []
    thread = meeting(id="thread/2026-11-08-release", kind="thread", lane=None)
    thread["source"] = {"room": "symphony:release-train", "sha256": DIGEST}
    assert knowledge_notes.errors(thread) == []
    daily = meeting(id="daily/2026-11-08", kind="daily", source=None, lane=None)
    assert knowledge_notes.errors({**daily, "lanes": ["ENG-12", "ENG-14"]}) == []
    runbook = meeting(id="runbook/restore", kind="runbook", origin=None, source=None)
    assert knowledge_notes.errors(runbook) == []


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"origin": None}, "needs origin"),
        ({"origin": "personal"}, "origin"),
        ({"source": None}, "needs a source"),
        ({"source": {"file": "a.vtt", "sha256": "abc"}}, "sha256"),
        ({"source": {"file": "a.vtt", "room": "r", "sha256": DIGEST}}, "exactly one"),
        ({"source": {"sha256": DIGEST}}, "exactly one"),
        ({"lane": "eng"}, "lane"),
        ({"id": "note/2026-11-08-roadmap"}, "id must start with meeting/"),
        ({"publish": {"site": "https://acme.atlassian.net", "space": "ENG"}}, "site"),
        ({"publish": {"site": WORK_SITE, "space": "ENG", "page_id": "1"}}, "together"),
        ({"publish": {"site": WORK_SITE, "space": "ENG", "extra": 1}}, "publish.extra"),
        ({"status": "accepted"}, "status and checks belong to decisions"),
    ],
)
def test_capture_schema_rejects(changes, message):
    found = knowledge_notes.errors(meeting(**changes))
    assert any(message in error for error in found), found


def test_publish_without_origin_is_refused_on_any_kind():
    note = meeting(id="note/x", kind="note", origin=None, source=None)
    note["publish"] = {"site": WORK_SITE, "space": "ENG"}
    assert any("published note needs origin" in e for e in knowledge_notes.errors(note))


def test_published_schema_states_the_capture_rules():
    published = json.loads((ROOT / "contracts/knowledge-note.schema.json").read_text())
    assert published == knowledge_notes.schema()
    assert {"origin", "lane", "source", "publish"} <= set(published["properties"])
    assert {"daily", "meeting", "thread"} <= set(published["properties"]["kind"]["enum"])
    rules = json.dumps(published["allOf"])
    assert '"required": ["origin"]' in rules and '"required": ["source"]' in rules
    assert published["$defs"]["Publish"]["dependentRequired"] == {
        "page_id": ["version"],
        "version": ["page_id"],
    }


# Dedupe


def test_source_digest_ignores_line_endings_and_finds_captured_notes(tmp_path):
    root = vault(tmp_path)
    text = b"WEBVTT\r\n\r\n00:00.000 --> 00:01.000\r\nAda: ship it\r\n"
    digest = knowledge_publish.source_sha256(text)
    assert digest == hashlib.sha256(text.replace(b"\r\n", b"\n")).hexdigest()
    transcript = tmp_path / "roadmap.vtt"
    transcript.write_bytes(text)
    assert knowledge_publish.check_source(root, transcript) == {
        "status": "new",
        "sha256": digest,
        "notes": [],
    }
    source = {"file": "Inbox/meetings/roadmap.vtt", "sha256": digest}
    write(root, "Meetings/2026-11-08-roadmap.md", meeting(source=source))
    (root / "Meetings/broken.md").write_text("---\n- not a mapping\n---\n")
    result = knowledge_publish.check_source(root, transcript)
    assert result["status"] == "captured"
    assert result["notes"] == ["Meetings/2026-11-08-roadmap.md"]


def test_captured_cli_exits_one_for_a_seen_source(tmp_path):
    root = vault(tmp_path)
    paste = tmp_path / "thread.txt"
    paste.write_text("ada: ship it\n")
    runner = CliRunner()
    first = runner.invoke(app, ["knowledge", "captured", str(paste), "--vault", str(root)])
    assert first.exit_code == 0, first.output
    digest = json.loads(first.output)["sha256"]
    source = {"room": "symphony:release", "sha256": digest}
    write(root, "Inbox/thread.md", meeting(id="thread/x", kind="thread", source=source))
    again = runner.invoke(app, ["knowledge", "captured", str(paste), "--vault", str(root)])
    assert again.exit_code == 1
    assert json.loads(again.output)["notes"] == ["Inbox/thread.md"]


# The wall


def test_plan_needs_a_declared_vault_target(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    note = write(root, "Meetings/m.md", meeting())
    result = knowledge_publish.plan(root, note)
    assert result["status"] == "refused"
    assert "no publish target" in result["reason"]


@pytest.mark.parametrize(
    ("origin", "site", "note_changes", "reason"),
    [
        ("home", HOME_SITE, {}, "origin mismatch: note is work, vault is home"),
        (
            "work",
            WORK_SITE,
            {"publish": {"site": HOME_SITE, "space": "SB"}},
            "site mismatch",
        ),
        ("work", WORK_SITE, {"id": "daily/2026-11-08", "kind": "daily"}, "daily notes stay"),
        ("work", WORK_SITE, {"lane": "nope"}, "invalid frontmatter"),
    ],
)
def test_plan_and_record_refuse_across_the_wall(tmp_path, origin, site, note_changes, reason):
    root = vault(tmp_path, origin=origin, site=site)
    note = write(root, "Meetings/m.md", meeting(**note_changes))
    before = (root / note).read_bytes()
    planned = knowledge_publish.plan(root, note)
    assert planned["status"] == "refused"
    assert reason in planned["reason"]
    recorded = knowledge_publish.record(root, note, "111", 1)
    assert recorded["status"] == "refused"
    assert (root / note).read_bytes() == before


def test_vault_target_rejects_urls_and_missing_fields(tmp_path):
    root = vault(tmp_path, site="https://acme.atlassian.net")
    with pytest.raises(ValueError, match="bare host name"):
        knowledge_publish.vault_target(root)
    (root / ".ai-dlc/publish.toml").write_text('site = "acme.atlassian.net"\nspace = "E"\n')
    with pytest.raises(ValueError, match="origin must be work or home"):
        knowledge_publish.vault_target(root)


# Plan, record and the version guard


def test_plan_shows_the_exact_outgoing_page_and_writes_nothing(tmp_path):
    root = vault(tmp_path)
    body = "# Roadmap sync\n\n## Decisions\n- Ship phase A\n<!-- ai-dlc:op-1:abc -->\n"
    note = write(root, "Meetings/m.md", meeting(), body)
    before = (root / note).read_bytes()
    planned = knowledge_publish.plan(root, note)
    assert planned == {
        "status": "ready",
        "action": "create",
        "note": note,
        "site": WORK_SITE,
        "space": "ENG",
        "parent": "98765",
        "page_id": None,
        "expected_version": None,
        "title": "Roadmap sync",
        "body": "# Roadmap sync\n\n## Decisions\n- Ship phase A\n",
    }
    assert "origin" not in planned["body"] and "sha256" not in planned["body"]
    assert (root / note).read_bytes() == before


def test_record_writes_the_binding_back_and_is_idempotent(tmp_path):
    root = vault(tmp_path)
    marker = "<!-- ai-dlc:capture-1:abc -->\n"
    note = "Meetings/m.md"
    (root / "Meetings").mkdir()
    (root / note).write_text(marker + front(meeting()))
    assert knowledge_publish.record(root, note, "4242", 1)["status"] == "recorded"
    text = (root / note).read_text()
    assert text.startswith(marker)
    data = knowledge_notes.split(knowledge_notes.strip_markers(text))[0]
    assert data["publish"] == {
        "site": WORK_SITE,
        "space": "ENG",
        "parent": "98765",
        "page_id": "4242",
        "version": 1,
    }
    assert data["source"]["sha256"] == DIGEST and knowledge_notes.errors(data) == []
    assert knowledge_publish.record(root, note, "4242", 1)["status"] == "unchanged"
    assert knowledge_publish.record(root, note, "9999", 2)["reason"].startswith(
        "page binding conflict"
    )
    assert knowledge_publish.record(root, note, "4242", 1)["status"] == "unchanged"


def test_update_refuses_a_page_changed_since_publish(tmp_path):
    root = vault(tmp_path)
    bound = {"site": WORK_SITE, "space": "ENG", "page_id": "4242", "version": 3}
    note = write(root, "Meetings/m.md", meeting(publish=bound))
    assert "current version first" in knowledge_publish.plan(root, note)["reason"]
    conflict = knowledge_publish.plan(root, note, remote_version=4)
    assert conflict["status"] == "refused"
    assert conflict["reason"].startswith("version conflict")
    assert (conflict["recorded_version"], conflict["remote_version"]) == (3, 4)
    ready = knowledge_publish.plan(root, note, remote_version=3)
    assert (ready["action"], ready["page_id"], ready["expected_version"]) == ("update", "4242", 3)
    stale = knowledge_publish.record(root, note, "4242", 2)
    assert stale["reason"].startswith("version conflict")
    assert knowledge_publish.record(root, note, "4242", 4)["status"] == "recorded"


def test_publish_cli_exit_codes(tmp_path):
    root = vault(tmp_path)
    note = write(root, "Meetings/m.md", meeting())
    runner = CliRunner()
    planned = runner.invoke(app, ["knowledge", "publish-plan", note, "--vault", str(root)])
    assert planned.exit_code == 0, planned.output
    assert json.loads(planned.output)["action"] == "create"
    args = ["knowledge", "publish-record", note, "--vault", str(root)]
    done = runner.invoke(app, [*args, "--page-id", "7", "--version", "1"])
    assert done.exit_code == 0, done.output
    other = runner.invoke(app, [*args, "--page-id", "8", "--version", "2"])
    assert other.exit_code == 1
    home = vault(tmp_path / "home", origin="home", site=HOME_SITE)
    write(home, "Meetings/m.md", meeting())
    refused = runner.invoke(app, ["knowledge", "publish-plan", note, "--vault", str(home)])
    assert refused.exit_code == 1
    assert json.loads(refused.output)["reason"].startswith("origin mismatch")


# The provider op


def test_publish_is_an_optional_knowledge_operation():
    roles = manifest()["roles"]
    assert roles["knowledge"] == {"mandatory": ["append"], "optional": ["publish"]}
    assert not manifest()["operations"]["publish"]["required"]
    published = json.loads((ROOT / "contracts/manifest.json").read_text())
    assert published == manifest()


def test_publish_request_and_response_contract():
    create = {
        "site": WORK_SITE,
        "space": "ENG",
        "parent": "98765",
        "title": "Roadmap sync",
        "body": "# Roadmap sync\n",
        "operation_id": "publish-meeting-2026-11-08-roadmap",
    }
    request = validate_request("publish", create)
    assert request.operation == "publish"
    assert request.operation_id == create["operation_id"]
    update = {**create, "page_id": "4242", "expected_version": 3}
    assert validate_request("publish", update).payload["expected_version"] == 3
    with pytest.raises(ValueError, match="together"):
        validate_request("publish", {**create, "page_id": "4242"})
    with pytest.raises(ValueError):
        validate_request("publish", {**create, "operation_id": ""})
    with pytest.raises(ValueError):
        validate_request("publish", {**create, "send_to": "everyone"})
    result = {"page_id": "4242", "version": 4, "url": f"https://{WORK_SITE}/wiki/x"}
    assert validate_response("publish", result)["version"] == 4
    with pytest.raises(ValueError):
        validate_response("publish", {"page_id": "4242", "version": 0, "url": "u"})
