"""KAN-481: two PRs that each add a feature and a changelog entry merge one after the other with
no conflict, because the entry is a fragment in changes/ and not an edit to CHANGELOG.md."""

import os
import runpy
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
changes = runpy.run_path(str(ROOT / "scripts" / "collect_changes.py"))

GIT = [
    "git",
    "-c",
    "user.name=t",
    "-c",
    "user.email=t@example.invalid",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "init.defaultBranch=main",
]


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run([*GIT, *args], cwd=repo, check=check, capture_output=True, text=True)


def write(repo: Path, rel: str, text: str) -> None:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    write(tmp_path, "CHANGELOG.md", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    write(tmp_path, "changes/README.md", "fragments\n")
    write(tmp_path, "src/one.py", "one = 1\n")
    write(tmp_path, "src/two.py", "two = 2\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def branch(repo: Path, name: str, files: dict[str, str]) -> None:
    git(repo, "checkout", "-qb", name, "main")
    for rel, text in files.items():
        write(repo, rel, text)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", name)
    git(repo, "checkout", "-q", "main")


def merge_both(repo: Path) -> list[int]:
    return [
        git(repo, "merge", "--no-ff", "-qm", f"merge {b}", b, check=False).returncode
        for b in ("a", "b")
    ]


def test_two_prs_with_fragments_merge_cleanly_and_collect(repo: Path) -> None:
    branch(
        repo, "a", {"src/one.py": "one = 11\n", "changes/KAN-1.added.md": "- One more (KAN-1).\n"}
    )
    branch(
        repo, "b", {"src/two.py": "two = 22\n", "changes/KAN-2.fixed.md": "- Two fixed (KAN-2).\n"}
    )
    assert merge_both(repo) == [0, 0]
    assert changes["problems"](repo) == []
    assert changes["main"](["--root", str(repo), "--write"]) == 0
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = text[text.index("## Unreleased") :]
    assert "- One more (KAN-1).\n" in unreleased and "- Two fixed (KAN-2).\n" in unreleased
    assert unreleased.index("### Added") < unreleased.index("- One more (KAN-1).")
    assert unreleased.index("### Fixed") < unreleased.index("- Two fixed (KAN-2).")
    assert [p.name for p in (repo / "changes").iterdir()] == ["README.md"]


def test_the_old_way_conflicts(repo: Path) -> None:
    """Why the fragments: two PRs adding a bullet at the top of the same section conflict."""
    log = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    at = log.index("### Added\n\n") + len("### Added\n\n")
    branch(repo, "a", {"CHANGELOG.md": log[:at] + "- One more.\n" + log[at:]})
    branch(repo, "b", {"CHANGELOG.md": log[:at] + "- Two fixed.\n" + log[at:]})
    assert merge_both(repo)[1] != 0


def test_fold_joins_an_existing_list() -> None:
    text = "# C\n\n## Unreleased\n\nIntro.\n\n### Added\n\n- old\n\n## v1\n"
    out = changes["fold"](text, {"Added": ["- new"], "Removed": ["- gone\n  wrapped"]})
    assert out == (
        "# C\n\n## Unreleased\n\nIntro.\n\n### Added\n\n- new\n- old\n\n"
        "### Removed\n\n- gone\n  wrapped\n\n## v1\n"
    )


def test_bad_fragments_are_named(tmp_path: Path) -> None:
    write(tmp_path, "changes/KAN-1.feature.md", "- x\n")
    write(tmp_path, "changes/KAN-2.md", "prose, no bullet\n")
    write(tmp_path, "changes/KAN-3.md", "### Added\n- x\n")
    got = changes["problems"](tmp_path)
    assert {p.split(":")[0] for p in got} == {
        "changes/KAN-1.feature.md",
        "changes/KAN-2.md",
        "changes/KAN-3.md",
    }


def test_this_repository_fragments_are_valid() -> None:
    assert changes["problems"](ROOT) == []


def changelog_edit_problems(root: Path, base: str) -> list[str]:
    """CHANGELOG.md modified since `base` without folding fragments (deleting changes/ files)."""
    names = git(root, "diff", "--name-status", base, "HEAD").stdout.splitlines()
    edited = any(x.startswith("M") and x.split("\t")[-1] == "CHANGELOG.md" for x in names)
    folded = any(x.startswith("D") and x.split("\t")[-1].startswith("changes/") for x in names)
    return (
        ["CHANGELOG.md: add changes/<KEY>.md instead; only the release fold edits it"]
        if (edited and not folded)
        else []
    )


def test_changelog_is_edited_only_by_the_fold() -> None:
    """In CI (AI_DLC_DOCS_BASE names the base), a change may not edit CHANGELOG.md directly."""
    base = os.environ.get("AI_DLC_DOCS_BASE")
    if not base or git(ROOT, "cat-file", "-e", f"{base}^{{commit}}", check=False).returncode:
        pytest.skip("no base commit to compare against")
    assert changelog_edit_problems(ROOT, base) == []


def test_the_changelog_check_tells_an_edit_from_a_fold(repo: Path) -> None:
    log = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    branch(repo, "edit", {"CHANGELOG.md": log + "- straight in.\n"})
    branch(repo, "fold", {"changes/KAN-1.md": "- one (KAN-1).\n"})
    git(repo, "checkout", "-q", "edit")
    assert changelog_edit_problems(repo, "main")
    git(repo, "checkout", "-q", "fold")
    assert changelog_edit_problems(repo, "main") == []
    git(repo, "tag", "with-fragment")
    assert changes["main"](["--root", str(repo), "--write"]) == 0
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "release fold")
    assert changelog_edit_problems(repo, "with-fragment") == []
