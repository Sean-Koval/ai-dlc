import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_layout.py"


def check(root):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_layout_reports_new_root_plan_and_flat_module(tmp_path):
    (tmp_path / "accidental-plan.md").write_text("# Draft\n")
    (tmp_path / "src/ai_dlc").mkdir(parents=True)
    (tmp_path / "src/ai_dlc/new_feature.py").write_text("")
    result = check(tmp_path)
    assert "accidental-plan.md" in result.stdout
    assert "src/ai_dlc/new_feature.py" in result.stdout
    assert result.returncode == 1


def test_layout_accepts_grouped_code_and_formal_change(tmp_path):
    (tmp_path / "src/ai_dlc/documentation").mkdir(parents=True)
    (tmp_path / "src/ai_dlc/documentation/review.py").write_text("")
    (tmp_path / "openspec/changes/feature").mkdir(parents=True)
    (tmp_path / "openspec/changes/feature/design.md").write_text("# Design\n")
    (tmp_path / "CLAUDE.md").write_text("@AGENTS.md\n")
    assert check(tmp_path).returncode == 0


def test_layout_rejects_tool_scratch_and_duplicate_claude_context(tmp_path):
    (tmp_path / ".superpowers").mkdir()
    (tmp_path / "CLAUDE.md").write_text("# Stale instructions\n@AGENTS.md\n")
    result = check(tmp_path)
    assert ".superpowers" in result.stdout
    assert "CLAUDE.md" in result.stdout
    assert result.returncode == 1


def test_layout_reports_a_dangling_claude_reference(tmp_path):
    (tmp_path / "CLAUDE.md").symlink_to(tmp_path / "missing.md")
    result = check(tmp_path)
    assert result.returncode == 1
    assert "CLAUDE.md" in result.stdout
