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
    """CHANGELOG.md modified since `base` other than by the release fold, which removes every
    fragment that was pending at `base`."""
    names = git(root, "diff", "--name-status", base, "HEAD").stdout.splitlines()
    if not any(x.startswith("M") and x.split("\t")[-1] == "CHANGELOG.md" for x in names):
        return []

    def pending(rev: str) -> set[str]:
        listed = git(root, "ls-tree", "-r", "--name-only", rev, "--", "changes/").stdout.split()
        return {p for p in listed if Path(p).name not in {"README.md", ".gitkeep"}}

    at_base = pending(base)
    if at_base and not at_base & pending("HEAD"):
        return []
    return ["CHANGELOG.md: add changes/<KEY>.md instead; only the release fold edits it"]


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
    # deleting one unrelated fragment doesn't make a direct edit a fold
    write(repo, "changes/KAN-2.md", "- two (KAN-2).\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "two")
    git(repo, "tag", "two-pending")  # KAN-1 and KAN-2 pending
    git(repo, "checkout", "-qb", "sneak")
    git(repo, "rm", "-q", "changes/KAN-2.md")
    write(repo, "CHANGELOG.md", log + "- straight in.\n")
    git(repo, "commit", "-qam", "sneak")
    assert changelog_edit_problems(repo, "two-pending")
    git(repo, "checkout", "-q", "fold")
    git(repo, "tag", "with-fragment")
    assert changes["main"](["--root", str(repo), "--write"]) == 0
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "release fold")
    assert changelog_edit_problems(repo, "with-fragment") == []


# KAN-49: a tag's release notes are its CHANGELOG.md section, never a fixed line.

RELEASED = """# Changelog

## Unreleased

### Added

- Something new.

## [0.5.0] - 2026-12-01

### Added

- The [session join key](docs/design/session-join-key.md) and [anchors](#unreleased).
- A [site](https://example.invalid/page) link stays as it is.

## [0.4.0] - 2026-09-14

First published release.
"""


def test_release_notes_are_the_versions_section_with_absolute_links() -> None:
    notes = changes["release_notes"](RELEASED, "0.5.0", "Sean-Koval/ai-dlc", "v0.5.0")
    assert notes.startswith("### Added\n\n- The [session join key]")
    assert (
        "(https://github.com/Sean-Koval/ai-dlc/blob/v0.5.0/docs/design/session-join-key.md)"
        in notes
    )
    assert "[anchors](#unreleased)" in notes
    assert "(https://example.invalid/page)" in notes
    assert "Something new" not in notes and "First published release" not in notes
    assert notes.endswith(changes["INSTALL_NOTE"] + "\n")


def test_release_notes_keep_relative_links_without_a_repository() -> None:
    notes = changes["release_notes"](RELEASED, "0.5.0")
    assert "](docs/design/session-join-key.md)" in notes


@pytest.mark.parametrize("version", ["0.6.0", "0.5", "Unreleased"])
def test_release_notes_refuse_a_version_the_changelog_lacks(version: str) -> None:
    with pytest.raises(ValueError, match="no '## \\["):
        changes["release_notes"](RELEASED, version)


def test_release_notes_refuse_an_empty_section() -> None:
    with pytest.raises(ValueError, match="is empty"):
        changes["release_notes"]("## [0.5.0] - 2026-12-01\n\n## [0.4.0]\n\nx\n", "0.5.0")


def test_release_notes_cli_fails_closed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "CHANGELOG.md", RELEASED)
    assert changes["main"](["--root", str(tmp_path), "--release-notes", "0.5.0"]) == 0
    assert capsys.readouterr().out.startswith("### Added")
    assert changes["main"](["--root", str(tmp_path), "--release-notes", "0.6.0"]) == 1
    assert "error: CHANGELOG.md has no '## [0.6.0]'" in capsys.readouterr().err


def test_this_changelogs_published_release_has_notes() -> None:
    notes = changes["release_notes"](
        (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), "0.4.0", "Sean-Koval/ai-dlc", "v0.4.0"
    )
    assert "hash-bound bootstrap assets" in notes


def test_a_tag_publishes_the_changelog_section_as_its_notes() -> None:
    import yaml

    jobs = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())["jobs"]
    step = next(s for s in jobs["package"]["steps"] if "CHANGELOG.md section" in s.get("name", ""))
    assert step["if"] == "github.event_name == 'push' && github.ref_type == 'tag'"
    assert "--release-notes" in step["run"] and "> dist/release-notes.md" in step["run"]
    publish = "\n".join(s.get("run", "") for s in jobs["publish"]["steps"])
    assert "--notes-file dist/release-notes.md" in publish
    assert "--notes " not in publish
