"""Migration of knowledge-note frontmatter to knowledge records (KAN-452, ADR 0005)."""

import json
import shutil
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.documentation import knowledge_migrate, knowledge_notes, knowledge_records
from ai_dlc.documentation.knowledge import Knowledge
from ai_dlc.documentation.knowledge_check import check_records
from ai_dlc.documentation.knowledge_publish import captured

FIXTURES = Path(__file__).parent / "fixtures/knowledge_notes"
MEETING_SHA = "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
TYPES = {
    "learning.md": "lesson",
    "decision.md": "decision",
    "rejected.md": "decision",
    "daily.md": "source",
    "meeting.md": "source",
    "thread.md": "source",
}


@pytest.fixture
def notes(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(FIXTURES, root)
    return root


def header(path: Path) -> dict:
    data, _raw, _body = knowledge_notes.split(knowledge_notes.strip_markers(path.read_text()))
    assert data is not None
    return data


def snapshot(root: Path) -> dict:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and ".ai-dlc" not in p.parts
    }


def test_fixtures_cover_every_old_kind_and_are_valid_notes():
    kinds = {header(path)["kind"] for path in FIXTURES.glob("*.md")}
    assert kinds == set(knowledge_notes.KINDS)
    for path in FIXTURES.glob("*.md"):
        assert knowledge_notes.errors(header(path)) == [], path


@pytest.mark.parametrize("name", sorted(TYPES))
def test_each_record_kind_migrates_to_a_valid_record(notes, name):
    knowledge_migrate.migrate(notes, write=True)
    data = header(notes / name)
    assert knowledge_records.errors(data) == []
    assert data["type"] == TYPES[name] and "kind" not in data
    assert data["aliases"] == [header(FIXTURES / name)["id"]]
    _old, _raw, old_body = knowledge_notes.split(
        knowledge_notes.strip_markers((FIXTURES / name).read_text())
    )
    assert (notes / name).read_text().endswith(old_body)


def test_field_mappings(notes):
    result = knowledge_migrate.migrate(notes, write=True)
    learning = header(notes / "learning.md")
    assert learning["id"] == "learning-2026-10-20-fix-receipts" and learning["status"] == "open"
    assert learning["sources"] == [
        {
            "resource": "https://github.com/o/r/pull/123",
            "hash": "git:0123456789abcdef0123456789abcdef01234567",
        }
    ]
    assert learning["stale_after"] == "2027-01-18T00:00:00Z"
    assert learning["links"] == [{"type": "belongs_to", "target": "fix-receipts"}]
    assert learning["owner"] == "octocat" and learning["label"] == "internal"
    dropped = {item["path"]: item["dropped"] for item in result["migrated"]}
    assert dropped["learning.md"] == ["repository"] and dropped["meeting.md"] == ["publish"]

    decision = header(notes / "decision.md")
    assert decision["id"] == "DEC-0007" and decision["status"] == "accepted"
    assert decision["links"] == [{"type": "supersedes", "target": "DEC-0006"}]
    assert decision["checks"] == header(FIXTURES / "decision.md")["checks"]
    assert decision["title"] == "0007 Landing stays in hangar"
    rejected = header(notes / "rejected.md")
    assert rejected["status"] == "rejected" and rejected["scope"] == "project"
    assert rejected["owner"] == "agent:claude-code"

    meeting = header(notes / "meeting.md")
    assert meeting["status"] == "raw" and meeting["label"] == "confidential"
    assert meeting["sources"] == [
        {"resource": "exports/planning.vtt", "hash": f"sha256:{MEETING_SHA}"}
    ]
    assert meeting["tags"] == ["meeting", "origin:work"] and meeting["provider"] == "notes"
    assert meeting["title"] == "Weekly planning" and meeting["observed_at"]
    text = (notes / "meeting.md").read_text()
    assert text.startswith("---\n") and "---\n<!-- ai-dlc:capture-1:aaaa -->\n# Weekly" in text
    assert header(notes / "thread.md")["sources"][0]["resource"] == "eng-chat"
    daily = header(notes / "daily.md")
    assert daily["sources"] == [{"resource": "daily.md"}]
    assert daily["links"] == [{"type": "belongs_to", "target": "KAN-8"}]


def test_runbook_and_note_stay_legacy_and_untouched(notes):
    result = knowledge_migrate.migrate(notes, write=True)
    assert result["status"] == "ok"
    assert result["legacy"] == [
        {"path": "note.md", "kind": "note"},
        {"path": "runbook.md", "kind": "runbook"},
    ]
    for name in ("note.md", "runbook.md"):
        assert (notes / name).read_bytes() == (FIXTURES / name).read_bytes()


def test_dry_run_writes_nothing(notes):
    before = snapshot(notes)
    result = knowledge_migrate.migrate(notes)
    assert result["mode"] == "dry-run" and len(result["migrated"]) == 6
    assert result["journal"] is None and snapshot(notes) == before
    assert not (notes / ".ai-dlc").exists()


def test_second_run_changes_nothing(notes):
    knowledge_migrate.migrate(notes, write=True)
    after = snapshot(notes)
    again = knowledge_migrate.migrate(notes, write=True)
    assert again["migrated"] == [] and again["journal"] is None
    assert again["unchanged"] == 6
    assert snapshot(notes) == after


def test_revert_restores_the_original_bytes(notes):
    before = snapshot(notes)
    journal = knowledge_migrate.migrate(notes, write=True)["journal"]
    assert journal.startswith(".ai-dlc/local/knowledge-migrate/")
    dry = knowledge_migrate.revert(notes, journal)
    assert len(dry["restored"]) == 6 and snapshot(notes) != before
    assert knowledge_migrate.revert(notes, journal, write=True)["status"] == "ok"
    assert snapshot(notes) == before
    assert knowledge_migrate.revert(notes, journal, write=True)["restored"] == []


def test_revert_leaves_files_edited_after_the_migration(notes):
    journal = knowledge_migrate.migrate(notes, write=True)["journal"]
    edited = (notes / "learning.md").read_text() + "Edited later.\n"
    (notes / "learning.md").write_text(edited)
    result = knowledge_migrate.revert(notes, journal, write=True)
    assert result["status"] == "conflict" and result["conflict"] == ["learning.md"]
    assert (notes / "learning.md").read_text() == edited
    assert (notes / "decision.md").read_bytes() == (FIXTURES / "decision.md").read_bytes()


def test_a_note_that_cannot_become_a_record_is_reported_not_written(notes):
    broken = notes / "broken.md"
    broken.write_text("---\nid: learning/x\nkind: learning\nscope: personal\n---\nBody\n")
    result = knowledge_migrate.migrate(notes, [Path("broken.md")], write=True)
    assert result["status"] == "invalid" and result["invalid"][0]["path"] == "broken.md"
    assert broken.read_text().startswith("---\nid: learning/x\n")


def test_migrated_bundle_passes_knowledge_check(notes):
    knowledge_migrate.migrate(notes, write=True)
    (notes / "knowledge.toml").write_text("[format]\nversion = 1\n")
    for name in ("note.md", "runbook.md"):
        (notes / name).unlink()
    # The superseded side of the fixture pair is rejected, not superseded, so mark it.
    rejected = (notes / "rejected.md").read_text()
    (notes / "rejected.md").write_text(
        rejected.replace("status: rejected", "status: superseded").replace(
            "valid_from:", "valid_to: 2026-10-20\nvalid_from:"
        )
    )
    result = check_records(notes)
    assert result["failures"] == [] and result["records"] == 6


def test_readers_accept_both_shapes(notes):
    learnings = notes / "learnings"
    learnings.mkdir()
    shutil.copy(FIXTURES / "learning.md", learnings / "old.md")
    shutil.copy(FIXTURES / "learning.md", learnings / "new.md")
    knowledge_migrate.migrate(notes, [Path("learnings/new.md")], write=True)

    report = knowledge_notes.check_vault(notes)
    assert report["status"] == "valid" and report["valid"] == 2
    assert report["deprecated"] == ["learnings/old.md"]
    assert knowledge_migrate.LEGACY_DROPPED_IN in report["deprecation"]

    found = {
        item["path"]: item for item in Knowledge(notes).recall(["receipt"], today=date(2027, 2, 1))
    }
    assert found["learnings/old.md"]["kind"] == "learning"
    assert found["learnings/old.md"]["stale"] is True
    assert found["learnings/new.md"]["type"] == "lesson"
    assert found["learnings/new.md"]["stale_after"] == "2027-01-18"
    assert found["learnings/new.md"]["stale"] is True
    fresh = Knowledge(notes).recall(["receipt"], today=date(2026, 12, 1))
    assert all(item["stale"] is False for item in fresh)


def test_capture_dedupe_finds_a_migrated_meeting(notes):
    assert captured(notes, MEETING_SHA) == ["meeting.md"]
    knowledge_migrate.migrate(notes, write=True)
    assert captured(notes, MEETING_SHA) == ["meeting.md"]


def test_cli_dry_run_write_and_revert(notes):
    runner = CliRunner()
    before = snapshot(notes)
    dry = runner.invoke(app, ["knowledge", "migrate", "--root", str(notes)])
    assert dry.exit_code == 0, dry.output
    assert json.loads(dry.output)["mode"] == "dry-run" and snapshot(notes) == before
    wrote = runner.invoke(app, ["knowledge", "migrate", "--root", str(notes), "--write"])
    journal = json.loads(wrote.output)["journal"]
    assert header(notes / "decision.md")["type"] == "decision"
    undo = ["knowledge", "migrate", "--root", str(notes), "--revert", journal, "--write"]
    assert runner.invoke(app, undo).exit_code == 0
    assert snapshot(notes) == before
    outside = runner.invoke(app, ["knowledge", "migrate", "--root", str(notes), "/"])
    assert outside.exit_code != 0


def test_note_schema_is_still_published_unchanged():
    root = Path(__file__).resolve().parents[1]
    published = json.loads((root / "contracts/knowledge-note.schema.json").read_text())
    assert published == knowledge_notes.schema()
