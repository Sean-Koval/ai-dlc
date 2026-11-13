"""Capture note kinds and source dedupe (ADR 0003).

The reviewed publish of a vault note is retired: `knowledge render` is the wiki's only
writer, tested in tests/test_knowledge_render.py (KAN-430).
"""

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
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
