"""The committed workflow plugin is a deterministic, digest-locked build of its sources."""

from __future__ import annotations

import hashlib
import json
import runpy
import shutil
import tomllib
from pathlib import Path

import pytest

from ai_dlc.harness import agents

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/ai-dlc-workflow"
BUILDER = runpy.run_path(str(ROOT / "scripts/build_workflow_plugin.py"))
TEAM_SKILLS = BUILDER["TEAM_SKILLS"]


def scratch_root(tmp_path: Path) -> Path:
    """A minimal checkout: the hook shim source, with skills from a private copy."""
    root = tmp_path / "checkout"
    shim = root / "src/ai_dlc/harness/hook_shim.py"
    shim.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "src/ai_dlc/harness/hook_shim.py", shim)
    shutil.copytree(ROOT / "agents", root / "agents")
    return root


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    checkout = scratch_root(tmp_path)
    monkeypatch.setattr(agents, "assets", lambda name: checkout / name)
    return checkout


def snapshot(directory: Path) -> dict[str, bytes]:
    return {
        p.relative_to(directory).as_posix(): p.read_bytes()
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }


def relock(checkout: Path) -> None:
    path = checkout / "agents/skills.lock.json"
    lock = json.loads(path.read_text())
    for entry in lock["skills"].values():
        entry["sha256"] = hashlib.sha256(
            (checkout / "agents" / entry["path"]).read_bytes()
        ).hexdigest()
    path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


def test_committed_plugin_is_current():
    assert BUILDER["drift"](ROOT) == []
    assert BUILDER["main"](["--check"]) == 0


def test_build_is_byte_deterministic(root):
    BUILDER["write"](root)
    first = snapshot(root / "plugins/ai-dlc-workflow")
    BUILDER["write"](root)
    second = snapshot(root / "plugins/ai-dlc-workflow")
    assert first == second
    lock = json.loads(first["plugin.lock.json"])
    manifest = json.loads(first[".claude-plugin/plugin.json"])
    assert manifest["metadata"]["content_digest"] == lock["content_digest"]
    assert lock["revision"] == 1 and manifest["version"].endswith("-r1")
    # The digest does not depend on where or when the build ran.
    for data in first.values():
        assert str(root).encode() not in data and str(ROOT).encode() not in data
    assert BUILDER["drift"](root) == []


def test_build_matches_the_committed_content_digest(root):
    planned = BUILDER["plan"](root)
    committed = json.loads((PLUGIN / "plugin.lock.json").read_text())
    assert json.loads(planned["plugin.lock.json"])["content_digest"] == committed["content_digest"]


def test_lock_lists_team_skills_guide_and_hooks_only():
    lock = json.loads((PLUGIN / "plugin.lock.json").read_text())
    assert lock["schema"] == 1 and lock["plugin"] == "ai-dlc-workflow"
    assert set(lock["components"]) == {f"skill:{n}" for n in TEAM_SKILLS} | {
        "guide:ai-dlc-workflow",
        "hooks:ai-dlc",
    }
    assert len(TEAM_SKILLS) == 10
    for excluded in ("day-start", "day-end"):
        assert f"skill:{excluded}" not in lock["components"]
        assert not (PLUGIN / "skills" / excluded).exists()
    canonical = json.dumps(lock["components"], sort_keys=True, separators=(",", ":")).encode()
    assert lock["content_digest"] == "sha256:" + hashlib.sha256(canonical).hexdigest()
    for name in TEAM_SKILLS:
        data = (PLUGIN / "skills" / name / "SKILL.md").read_bytes()
        assert data == (ROOT / "agents/skills" / name / "SKILL.md").read_bytes()
        assert lock["components"][f"skill:{name}"] == "sha256:" + hashlib.sha256(data).hexdigest()


def test_manifest_is_opt_in_and_versioned_by_revision():
    manifest = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())
    lock = json.loads((PLUGIN / "plugin.lock.json").read_text())
    from ai_dlc import __version__

    assert manifest["name"] == "ai-dlc-workflow"
    assert manifest["defaultEnabled"] is False
    assert manifest["version"] == f"{__version__}-r{lock['revision']}"
    assert manifest["metadata"]["content_digest"] == lock["content_digest"]
    assert "mcpServers" not in manifest


def test_hooks_use_exec_form_and_the_shim():
    document = json.loads((PLUGIN / "hooks/hooks.json").read_text())
    assert set(document["hooks"]) == {"SessionStart", "PreToolUse", "Stop"}
    actions = {"SessionStart": "session-start", "PreToolUse": "pre-tool", "Stop": "stop"}
    for event, entries in document["hooks"].items():
        (entry,) = entries
        (hook,) = entry["hooks"]
        assert hook == {
            "type": "command",
            "command": "python3",
            "args": ["${CLAUDE_PLUGIN_ROOT}/hooks/aidlc_hook.py", actions[event]],
            "timeout": 10,
        }
        assert entry.get("matcher") == ("Bash|exec_command" if event == "PreToolUse" else None)


def test_skill_digest_mismatch_is_refused(root, capsys):
    skill = root / "agents/skills/needs-spec/SKILL.md"
    skill.write_bytes(skill.read_bytes() + b" ")
    with pytest.raises(ValueError, match="skill digest mismatch: needs-spec"):
        BUILDER["plan"](root)
    assert BUILDER["main"](["--root", str(root)]) == 1
    assert "skill digest mismatch" in capsys.readouterr().err


def test_relocked_skill_edit_without_rebuild_is_stale(root, capsys):
    BUILDER["write"](root)
    skill = root / "agents/skills/needs-spec/SKILL.md"
    skill.write_bytes(skill.read_bytes() + b"\n")
    relock(root)
    stale = BUILDER["drift"](root)
    assert "skills/needs-spec/SKILL.md" in stale and "plugin.lock.json" in stale
    assert BUILDER["main"](["--check", "--root", str(root)]) == 1
    assert "Workflow plugin is stale" in capsys.readouterr().err
    BUILDER["write"](root)
    manifest = json.loads((root / "plugins/ai-dlc-workflow/.claude-plugin/plugin.json").read_text())
    assert manifest["version"].endswith("-r2")
    assert BUILDER["drift"](root) == []


def test_unexpected_files_are_stale_and_removed_but_readme_is_authored(root):
    BUILDER["write"](root)
    plugin = root / "plugins/ai-dlc-workflow"
    (plugin / "README.md").write_text("authored\n")
    (plugin / "skills/day-start").mkdir()
    (plugin / "skills/day-start/SKILL.md").write_text("stale\n")
    assert BUILDER["drift"](root) == ["skills/day-start/SKILL.md"]
    BUILDER["write"](root)
    assert not (plugin / "skills/day-start").exists()
    assert (plugin / "README.md").read_text() == "authored\n"


def test_guide_keeps_only_provider_neutral_guidance():
    portable, adopted = BUILDER["guidance_lines"]()
    guide = (PLUGIN / "skills/ai-dlc-workflow/SKILL.md").read_text()
    assert guide == BUILDER["guide_skill"]()
    assert guide.startswith("---\nname: ai-dlc-workflow\ndescription: ")
    lowered = guide.lower()
    for leak in ["openspec", "obsidian", "github", "jira", "linear", "provider", "## verification"]:
        assert leak not in lowered
    project = tomllib.loads((ROOT / "ai-dlc.toml").read_text())
    for command in project["checks"]["commands"].values():
        assert command not in guide
    assert "ai-dlc project check" not in guide
    assert portable and adopted
    assert all("ai-dlc" not in line for line in portable)
    for line in adopted:
        assert "ai-dlc" in line
    assert (
        "If `ai-dlc.toml` exists at the repo root and `ai-dlc` is on PATH: complete work "
        "through `ai-dlc work finish`." in guide
    )
    for line in guide.splitlines():
        if "`ai-dlc " in line and line.startswith("- "):
            assert line.startswith(f"- {BUILDER['ADOPTED']}")
    assert "prefer the repository copies" in guide
