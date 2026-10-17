"""Knowledge-note frontmatter for learnings: generation, validation, recall and checks."""

import json
from datetime import date
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.documentation import knowledge_notes
from ai_dlc.documentation.knowledge import Knowledge
from ai_dlc.harness.hooks import handle_hook

ROOT = Path(__file__).resolve().parents[1]
MERGE_SHA = "0123456789abcdef0123456789abcdef01234567"


def valid_learning(**changes):
    note = {
        "id": "learning/2026-10-20-fix-receipts",
        "kind": "learning",
        "scope": "personal",
        "label": "internal",
        "sources": [{"uri": "https://github.com/o/r/pull/123", "hash": f"git:{MERGE_SHA}"}],
        "author": "human:octocat",
        "confidence": "medium",
        "valid_from": "2026-10-20",
        "valid_to": None,
        "review_by": "2027-01-18",
        "supersedes": [],
        "work": "fix-receipts",
        "repository": "o/r",
    }
    note.update(changes)
    return note


def front(fields, body="## What happened\nA lesson\n"):
    return "---\n" + knowledge_notes.dump(fields) + "---\n" + body


def test_schema_file_is_generated_from_the_model():
    published = json.loads((ROOT / "contracts/knowledge-note.schema.json").read_text())
    assert published == knowledge_notes.schema()
    assert set(published["properties"]) >= {
        "id",
        "kind",
        "scope",
        "label",
        "sources",
        "author",
        "confidence",
        "valid_from",
        "valid_to",
        "review_by",
        "supersedes",
        "work",
        "repository",
    }


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"sources": []}, "at least one source"),
        ({"author": "octocat"}, "author"),
        ({"scope": "company"}, "scope"),
        ({"id": "decision/2026-10-20-x"}, "id must start with learning/"),
        ({"status": "accepted"}, "status and checks belong to decisions"),
        ({"valid_to": "2026-01-01"}, "valid_to precedes valid_from"),
    ],
)
def test_learning_schema_rejects(changes, message):
    found = knowledge_notes.errors(valid_learning(**changes))
    assert any(message in error for error in found), found


def test_split_refuses_oversized_and_non_mapping_frontmatter():
    with pytest.raises(ValueError, match="64 KB"):
        knowledge_notes.split("x" * (64 * 1024 + 1))
    with pytest.raises(ValueError, match="mapping"):
        knowledge_notes.split("---\n- a\n---\nbody")
    assert knowledge_notes.split("no frontmatter") == (None, "", "no frontmatter")


# --- work finish --learning -------------------------------------------------------------


class Tracker:
    def __init__(self):
        self.items = [{"id": "1", "url": "https://issues/1", "state": "open"}]

    def invoke(self, op, data):
        if op == "find":
            return {"items": []}
        if op == "transition":
            self.items[0]["state"] = "closed"
        return self.items[0]


class Registry:
    def __init__(self, provider):
        self.provider = provider

    def get(self, _id):
        return self.provider


@pytest.fixture
def finished(tmp_path, monkeypatch):
    from ai_dlc.work import workflow

    class SCM:
        def __init__(self, root, config):
            pass

        def merged(self, reference):
            return {
                "sha": MERGE_SHA,
                "pr": {"merged": True, "html_url": "https://github.com/o/r/pull/45"},
            }

        def ci(self, sha):
            return {"sha": sha, "run_id": 99, "receipt": {}}

    monkeypatch.setattr(workflow, "GitHubSCM", SCM)
    monkeypatch.delenv("AI_DLC_AUTHOR", raising=False)
    folder = tmp_path / ".ai-dlc/work"
    folder.mkdir(parents=True)
    (folder / "fix-receipts.toml").write_text(
        'schema=1\nid="fix-receipts"\ntitle="Fix receipts"\nscope="small"\n'
        'requires_spec=false\nspec_reason="No behavior change"\nacceptance=["Tests pass"]\n'
        'reviewed=true\n[providers]\ntracker="fake"\n'
    )
    vault = tmp_path / "vault"
    vault.mkdir()
    service = workflow.WorkService(
        tmp_path,
        {"paths": {"vault": str(vault)}, "scm": {"repository": "o/r"}},
        state_path=tmp_path / "state",
        registry=Registry(Tracker()),
    )
    service.publish("fix-receipts")
    return service, vault


def stored(vault):
    (note,) = (vault / "learnings").glob("*-fix-receipts.md")
    return note


def test_finish_generates_valid_frontmatter_with_gate_provenance(finished):
    service, vault = finished
    result = service.finish("fix-receipts", learning="## What happened\nRetry the receipt.\n")
    assert result["status"] == "completed", result
    text = stored(vault).read_text()
    data, _raw, body = knowledge_notes.split(text)
    assert data is not None
    assert knowledge_notes.errors(data) == []
    assert data["sources"] == [
        {"uri": "https://github.com/o/r/pull/45", "hash": f"git:{MERGE_SHA}"},
        {"uri": "https://github.com/o/r/actions/runs/99", "hash": f"git:{MERGE_SHA}"},
    ]
    start = data["valid_from"]
    assert data["id"] == f"learning/{start.isoformat()}-fix-receipts"
    assert (data["review_by"] - start).days == 90
    assert data["scope"] == "personal" and data["confidence"] == "medium"
    assert data["author"] == "agent:unknown"
    assert data["work"] == "fix-receipts" and data["repository"] == "o/r"
    assert body.startswith("## What happened\nRetry the receipt.")


def test_finish_keeps_every_supplied_field(finished, monkeypatch):
    service, vault = finished
    monkeypatch.setenv("AI_DLC_AUTHOR", "agent:claude-code@sha256:abc")
    body = "---\nconfidence: high\nscope: project   # widened by a person\n---\nLesson\n"
    assert service.finish("fix-receipts", learning=body)["status"] == "completed"
    text = stored(vault).read_text()
    assert text.startswith("---\nconfidence: high\nscope: project   # widened by a person\n")
    data, _raw, _body = knowledge_notes.split(text)
    assert data["confidence"] == "high" and data["scope"] == "project"
    assert data["author"] == "agent:claude-code@sha256:abc"
    assert knowledge_notes.errors(data) == []


def test_finish_with_invalid_supplied_frontmatter_leaves_learning_pending(finished):
    service, vault = finished
    result = service.finish("fix-receipts", learning="---\nconfidence: certain\n---\nLesson\n")
    assert result["status"] == "completed,learning_pending"
    assert "confidence" in result["learning_error"]
    assert not (vault / "learnings").exists()


def test_finish_retry_is_byte_identical_and_conflicts_on_new_body(finished, monkeypatch):
    service, vault = finished
    first = service.finish("fix-receipts", learning="Lesson\n")
    before = stored(vault).read_bytes()
    from ai_dlc.documentation import learnings

    class LaterDay:
        @staticmethod
        def now(zone):
            raise AssertionError("retry must reuse the saved note")

    monkeypatch.setattr(learnings, "datetime", LaterDay)
    monkeypatch.setenv("AI_DLC_AUTHOR", "human:someone-else")
    second = service.finish("fix-receipts", learning="Lesson\n")
    assert first["learning"] == second["learning"]
    assert stored(vault).read_bytes() == before
    conflict = service.finish("fix-receipts", learning="Another lesson\n")
    assert conflict["status"] == "completed,learning_pending"
    assert "conflict" in conflict["learning_error"]
    assert stored(vault).read_bytes() == before


def test_finish_retry_after_unavailable_vault_writes_the_journaled_note(finished):
    service, vault = finished
    service.config["paths"] = {}
    assert (
        service.finish("fix-receipts", learning="Lesson\n")["status"]
        == "completed,learning_pending"
    )
    service.config["paths"] = {"vault": str(vault)}
    assert service.finish("fix-receipts", learning="Lesson\n")["status"] == "completed"
    assert knowledge_notes.split(stored(vault).read_text())[0]["kind"] == "learning"


def test_author_resolution_is_explicit(monkeypatch):
    import subprocess

    from ai_dlc.documentation import learnings

    monkeypatch.setenv("AI_DLC_AUTHOR", "codex@sha256:1")
    assert learnings.resolve_author(interactive=True) == "agent:codex@sha256:1"
    monkeypatch.delenv("AI_DLC_AUTHOR")
    assert learnings.resolve_author(interactive=False) == "agent:unknown"
    monkeypatch.setattr(
        learnings.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="octocat\n"),
    )
    assert learnings.resolve_author(interactive=True) == "human:octocat"


# --- recall -----------------------------------------------------------------------------


def write_learning(vault, name, **changes):
    (vault / "learnings").mkdir(parents=True, exist_ok=True)
    path = vault / "learnings" / name
    path.write_text(front(valid_learning(**changes), "Retry lesson " + name + "\n"))
    return path


def test_recall_skips_expired_flags_stale_and_keeps_old_notes(tmp_path):
    write_learning(tmp_path, "current.md", review_by="2027-01-18")
    write_learning(tmp_path, "stale.md", review_by="2026-11-01")
    write_learning(tmp_path, "expired.md", valid_to="2026-10-30")
    (tmp_path / "learnings/old.md").write_text("Retry lesson from before the schema\n")
    found = Knowledge(tmp_path).recall(["retry"], today=date(2026, 12, 1))
    by_path = {note["path"]: note for note in found}
    assert set(by_path) == {"learnings/current.md", "learnings/stale.md", "learnings/old.md"}
    assert by_path["learnings/old.md"] == {
        "path": "learnings/old.md",
        "first_line": "Retry lesson from before the schema",
    }
    assert by_path["learnings/current.md"] == {
        "path": "learnings/current.md",
        "first_line": "Retry lesson current.md",
        "kind": "learning",
        "author": "human:octocat",
        "review_by": "2027-01-18",
        "stale": False,
    }
    assert by_path["learnings/stale.md"]["stale"] is True


def test_session_hook_prefixes_stale_notes(tmp_path, monkeypatch):
    from ai_dlc.harness import hooks

    monkeypatch.setattr(
        hooks,
        "_session_recall",
        lambda root: [
            {"path": "learnings/a.md", "first_line": "Fresh", "stale": False},
            {"path": "learnings/b.md", "first_line": "Old", "stale": True},
        ],
    )
    context = handle_hook(tmp_path, "session-start", {})["context"]
    assert "learnings/a.md: Fresh" in context
    assert "(stale) learnings/b.md: Old" in context


# --- knowledge check --------------------------------------------------------------------


def test_knowledge_check_cli_exit_codes(tmp_path):
    write_learning(tmp_path, "good.md")
    (tmp_path / "learnings/legacy.md").write_text("---\nwork: one\npr: 1\n---\nOld\n")
    (tmp_path / "notes.md").write_text("---\nkind: learning\n---\nOutside learnings/\n")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = CliRunner().invoke(app, ["knowledge", "check", "--vault", str(tmp_path)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["valid"] == 1 and report["legacy"] == ["learnings/legacy.md"]

    write_learning(tmp_path, "bad.md", sources=[])
    result = CliRunner().invoke(app, ["knowledge", "check", "--vault", str(tmp_path)])
    assert result.exit_code == 1
    report = json.loads(result.output)
    assert [item["path"] for item in report["invalid"]] == ["learnings/bad.md"]
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert all(after[path] == content for path, content in before.items())


def test_generated_note_round_trips_through_yaml():
    note = knowledge_notes.with_missing("Body\n", {"id": "learning/x", "valid_to": None})
    assert yaml.safe_load(note.split("---\n")[1]) == {"id": "learning/x", "valid_to": None}
    assert knowledge_notes.with_missing(note, {"id": "learning/y"}) == note
