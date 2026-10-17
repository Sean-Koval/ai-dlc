"""Publishing the workflow plugin into a team harness directory."""

from __future__ import annotations

import hashlib
import json
import runpy
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = runpy.run_path(str(ROOT / "scripts/publish_workflow_plugin.py"))
PLUGIN = ROOT / "plugins/ai-dlc-workflow"


def run(capsys, harness: Path, mode: str) -> tuple[int, dict | str]:
    code = PUBLISH["main"](["--harness-repo", str(harness), mode])
    out = capsys.readouterr()
    return code, (json.loads(out.out) if code == 0 else out.err)


def test_dry_run_lists_files_and_component_ids_without_writing(tmp_path, capsys):
    harness = tmp_path / "harness"
    code, report = run(capsys, harness, "--dry-run")
    assert code == 0 and isinstance(report, dict)
    assert report["status"] == "planned"
    assert not harness.exists()
    paths = {c["path"] for c in report["changes"]}
    assert "plugins/ai-dlc-workflow/.claude-plugin/plugin.json" in paths
    assert "plugins/ai-dlc-workflow/README.md" in paths
    assert "native/codex/ai-dlc-workflow/hooks.json" in paths
    assert "native/codex/ai-dlc-workflow/skills/needs-spec/SKILL.md" in paths
    assert not any(p.startswith("plugins/ai-dlc-workflow/native/") for p in paths)
    lock = json.loads((PLUGIN / "plugin.lock.json").read_text())
    ids = [c["id"] for c in report["components"]]
    assert f"plugin:ai-dlc-workflow@{lock['content_digest']}" in ids
    assert f"skill:needs-spec@{lock['components']['skill:needs-spec']}" in ids
    assert "native:codex/ai-dlc-workflow/hooks.json" in ids
    assert report["marketplace_entry"] == {
        "name": "ai-dlc-workflow",
        "source": "./plugins/ai-dlc-workflow",
        "defaultEnabled": False,
    }
    assert report["source"].startswith("git:https://github.com/Sean-Koval/ai-dlc#")


def test_apply_writes_then_second_apply_is_a_no_op(tmp_path, capsys):
    harness = tmp_path / "harness"
    (harness / "skills/own").mkdir(parents=True)
    (harness / "skills/own/SKILL.md").write_text("the team's own skill\n")
    code, report = run(capsys, harness, "--apply")
    assert code == 0 and isinstance(report, dict) and report["status"] == "applied"
    published = harness / "plugins/ai-dlc-workflow"
    for path in (PLUGIN).rglob("*"):
        relative = path.relative_to(PLUGIN)
        if path.is_file() and relative.parts[0] != "native":
            assert (published / relative).read_bytes() == path.read_bytes()
    native = harness / "native/codex/ai-dlc-workflow"
    assert (native / "AGENTS.fragment.md").read_bytes() == (
        PLUGIN / "native/codex/AGENTS.fragment.md"
    ).read_bytes()
    assert not (published / "native").exists()
    plugin_component = report["components"][0]
    tree = {
        p.relative_to(published).as_posix(): p.read_bytes()
        for p in sorted(published.rglob("*"))
        if p.is_file()
    }
    assert plugin_component["hangar_files_digest"] == PUBLISH["files_digest"](tree)
    code, again = run(capsys, harness, "--apply")
    assert code == 0 and isinstance(again, dict)
    assert again["status"] == "unchanged" and again["changes"] == []
    assert (harness / "skills/own/SKILL.md").read_text() == "the team's own skill\n"


@pytest.mark.parametrize(
    "edit",
    [
        "plugins/ai-dlc-workflow/skills/needs-spec/SKILL.md",
        "plugins/ai-dlc-workflow/README.md",
        "native/codex/ai-dlc-workflow/hooks.json",
    ],
)
def test_hand_edited_target_is_refused(tmp_path, capsys, edit):
    harness = tmp_path / "harness"
    assert run(capsys, harness, "--apply")[0] == 0
    target = harness / edit
    target.write_bytes(target.read_bytes() + b"\nlocal tweak\n")
    before = target.read_bytes()
    code, error = run(capsys, harness, "--apply")
    assert code == 1 and "edited after publication" in str(error)
    assert target.read_bytes() == before


def test_unknown_files_in_the_target_are_refused(tmp_path, capsys):
    harness = tmp_path / "harness"
    assert run(capsys, harness, "--apply")[0] == 0
    extra = harness / "plugins/ai-dlc-workflow/skills/team-extra/SKILL.md"
    extra.parent.mkdir()
    extra.write_text("not ours\n")
    code, error = run(capsys, harness, "--dry-run")
    assert code == 1 and "did not publish" in str(error)


def test_foreign_target_directory_is_refused(tmp_path, capsys):
    harness = tmp_path / "harness"
    (harness / "plugins/ai-dlc-workflow").mkdir(parents=True)
    (harness / "plugins/ai-dlc-workflow/notes.md").write_text("someone else's\n")
    code, error = run(capsys, harness, "--apply")
    assert code == 1 and "plugin.lock.json" in str(error)
    assert (harness / "plugins/ai-dlc-workflow/notes.md").exists()


def test_legacy_publication_without_file_digests_is_replaced(tmp_path, capsys):
    """A snapshot from before per-file digests (agent-factory's first one) is proven by components."""
    harness = tmp_path / "harness"
    target = harness / "plugins/ai-dlc-workflow"
    shutil.copytree(PLUGIN, target, ignore=shutil.ignore_patterns("native"))
    lock = json.loads((target / "plugin.lock.json").read_text())
    lock.pop("files")
    lock.pop("native")
    (target / "plugin.lock.json").write_text(json.dumps(lock))
    code, report = run(capsys, harness, "--apply")
    assert code == 0 and isinstance(report, dict) and report["status"] == "applied"
    assert (target / "plugin.lock.json").read_bytes() == (PLUGIN / "plugin.lock.json").read_bytes()

    shutil.rmtree(harness)
    shutil.copytree(PLUGIN, target, ignore=shutil.ignore_patterns("native"))
    (target / "plugin.lock.json").write_text(json.dumps(lock))
    skill = target / "skills/handoff/SKILL.md"
    skill.write_text("edited\n")
    code, error = run(capsys, harness, "--apply")
    assert code == 1 and "edited after publication" in str(error)


def test_stale_build_is_refused(tmp_path, capsys, monkeypatch):
    builder = PUBLISH["_builder"]()
    monkeypatch.setitem(
        PUBLISH["source_files"].__globals__,
        "_builder",
        lambda: type("B", (), {"drift": staticmethod(lambda root: ["plugin.lock.json"])})(),
    )
    code, error = run(capsys, tmp_path / "harness", "--dry-run")
    assert code == 1 and "stale" in str(error)
    assert builder.drift(ROOT) == []


def test_files_digest_matches_hangars_definition():
    import hashlib

    files = {"b/x": b"1", "a": b"2", "a.b/c": b"3"}
    expected = hashlib.sha256()
    for rel in ["a", "a.b/c", "b/x"]:
        expected.update(rel.encode() + b"\0" + hashlib.sha256(files[rel]).digest())
    assert PUBLISH["files_digest"](files) == "sha256:" + expected.hexdigest()


def test_marketplace_layout_publishes_under_the_marketplace_directory(tmp_path, capsys):
    harness = tmp_path / "harness"
    entries = harness / "plugins/team/.claude-plugin/marketplace.json"
    entries.parent.mkdir(parents=True)
    entry = {
        "name": "ai-dlc-workflow",
        "source": "./ai-dlc-workflow",
        "defaultEnabled": False,
        "x": 1,
    }
    entries.write_text(json.dumps({"name": "team", "plugins": [entry]}))
    before = entries.read_bytes()
    code = PUBLISH["main"](["--harness-repo", str(harness), "--marketplace", "team", "--apply"])
    report = json.loads(capsys.readouterr().out)
    assert code == 0 and report["status"] == "applied"
    target = harness / "plugins/team/ai-dlc-workflow"
    assert (target / ".claude-plugin/plugin.json").is_file()
    assert not (harness / "plugins/ai-dlc-workflow").exists()
    assert entries.read_bytes() == before  # the harness owns its marketplace.json
    assert report["plugin_path"] == "plugins/team/ai-dlc-workflow"
    assert report["marketplace_entry"] == entry
    plugin = report["components"][0]
    assert plugin["lock_id"] == "plugin:ai-dlc-workflow@team"
    files = {
        p.relative_to(target).as_posix(): p.read_bytes()
        for p in sorted(target.rglob("*"))
        if p.is_file()
    }
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256(f"{canonical}\n{PUBLISH['files_digest'](files)}".encode()).hexdigest()
    assert plugin["hangar_plugin_digest"] == "sha256:" + expected
    code = PUBLISH["main"](["--harness-repo", str(harness), "--marketplace", "team", "--apply"])
    assert code == 0 and json.loads(capsys.readouterr().out)["status"] == "unchanged"


def test_marketplace_without_entry_suggests_a_relative_source(tmp_path, capsys):
    code = PUBLISH["main"](
        ["--harness-repo", str(tmp_path / "h"), "--marketplace", "team", "--dry-run"]
    )
    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["marketplace_entry"] == {
        "name": "ai-dlc-workflow",
        "source": "./ai-dlc-workflow",
        "defaultEnabled": False,
    }
    assert (
        PUBLISH["main"](["--harness-repo", str(tmp_path), "--marketplace", "../x", "--dry-run"])
        == 1
    )
