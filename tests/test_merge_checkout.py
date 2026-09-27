from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest
from fixtures.git import git

from ai_dlc.files import GitError
from ai_dlc.work.merge_checkout import (
    allocate_checkout,
    recover_checkout,
    repository_common_dir,
    require_merge_commit,
)


def _repository(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "caller with spaces-δ"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "AI-DLC Test")
    git(root, "config", "user.email", "ai-dlc@example.test")
    (root / ".gitignore").write_text("ignored.log\n")
    (root / "tracked.txt").write_text("first\n")
    git(root, "add", ".gitignore", "tracked.txt")
    git(root, "commit", "-m", "first")
    first = git(root, "rev-parse", "HEAD")
    (root / "tracked.txt").write_text("second\n")
    git(root, "commit", "-am", "second")
    return root, first, git(root, "rev-parse", "HEAD")


def _allocate(tmp_path: Path, root: Path, revision: str):
    common = repository_common_dir(root)
    checkout = allocate_checkout(
        caller_root=root,
        common_dir=common,
        state_dir=tmp_path / "private state-δ",
        work_id="one",
        revision=revision,
    )
    return common, checkout


def test_common_directory_is_absolute_and_shared_by_linked_worktrees(tmp_path: Path):
    root, _, _ = _repository(tmp_path)
    linked = tmp_path / "other worktree"
    git(root, "worktree", "add", "--detach", str(linked), "HEAD")

    common = repository_common_dir(root)

    assert common.is_absolute()
    assert repository_common_dir(linked) == common


def test_common_directory_reads_git_paths_as_filesystem_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import ai_dlc.work.merge_checkout as lifecycle

    root, _, _ = _repository(tmp_path)
    real_run_git = lifecycle.run_git
    text_modes: list[bool | None] = []

    def run_git(root_arg, *args, **kwargs):
        if args == ("rev-parse", "--path-format=absolute", "--git-common-dir"):
            text_modes.append(kwargs.get("text"))
        return real_run_git(root_arg, *args, **kwargs)

    monkeypatch.setattr(lifecycle, "run_git", run_git)

    assert repository_common_dir(root) == root / ".git"
    assert text_modes == [False, False]


def test_unicode_checkout_lifecycle_ignores_an_incompatible_text_output_codec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import subprocess

    root, _, _ = _repository(tmp_path)
    (root / "tracked.txt").write_text("unicode commit\n")
    subprocess.run(
        ["git", "-C", str(root), "commit", "-am", "unicode subject Ё"],
        capture_output=True,
        check=True,
        text=False,
        timeout=10,
    )
    revision = git(root, "rev-parse", "HEAD")
    real_run = subprocess.run

    def run(command, **kwargs):
        if kwargs.get("text"):
            binary_kwargs = {**kwargs, "text": False}
            result = real_run(command, **binary_kwargs)
            return subprocess.CompletedProcess(
                result.args,
                result.returncode,
                result.stdout.decode("cp1252"),
                result.stderr.decode("cp1252"),
            )
        return real_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    common, owned = _allocate(tmp_path, root, revision)

    owned.create()
    result = owned.cleanup()

    assert result.status == "removed"
    assert not owned.marker.parent.exists()
    assert repository_common_dir(root) == common


def test_common_directory_rejects_a_symlinked_repository_path(tmp_path: Path):
    root, _, _ = _repository(tmp_path)
    alias = tmp_path / "repository alias"
    try:
        alias.symlink_to(root, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")

    with pytest.raises(ValueError, match="symlink|reparse|identity"):
        repository_common_dir(alias)


def test_require_merge_commit_accepts_an_exact_unreferenced_commit(tmp_path: Path):
    root, first, _ = _repository(tmp_path)
    git(root, "branch", "temporary", first)
    git(root, "branch", "-D", "temporary")

    require_merge_commit(root, first, "example/project")
    require_merge_commit(root, first.upper(), "example/project")


@pytest.mark.parametrize("revision", ["main", "abc", "g" * 40, "0" * 40])
def test_require_merge_commit_rejects_names_invalid_ids_and_missing_objects(
    tmp_path: Path, revision: str
):
    root, _, _ = _repository(tmp_path)

    with pytest.raises(ValueError) as failure:
        require_merge_commit(root, revision, "example/project")

    reason = str(failure.value)
    assert "example/project" in reason
    assert revision in reason
    assert "fetch" in reason.lower()


def test_require_merge_commit_rejects_a_noncommit_object(tmp_path: Path):
    root, _, _ = _repository(tmp_path)
    blob = git(root, "hash-object", "-w", "tracked.txt")

    with pytest.raises(ValueError, match="fetch"):
        require_merge_commit(root, blob, "example/project")


def test_require_merge_commit_rejects_an_annotated_tag_object(tmp_path: Path):
    root, _, _ = _repository(tmp_path)
    git(root, "tag", "-a", "release", "-m", "release")
    tag_object = git(root, "rev-parse", "release^{tag}")

    with pytest.raises(ValueError, match="fetch"):
        require_merge_commit(root, tag_object, "example/project")


def test_allocate_rejects_a_symlinked_state_namespace_before_writing_through_it(
    tmp_path: Path,
):
    root, first, _ = _repository(tmp_path)
    common = repository_common_dir(root)
    foreign = tmp_path / "foreign state"
    foreign.mkdir()
    alias = tmp_path / "state alias"
    try:
        alias.symlink_to(foreign, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")

    with pytest.raises(ValueError, match="symlink|reparse|identity"):
        allocate_checkout(
            caller_root=root,
            common_dir=common,
            state_dir=alias,
            work_id="one",
            revision=first,
        )

    assert list(foreign.iterdir()) == []


def test_create_uses_exact_detached_revision_and_cleanup_preserves_caller(
    tmp_path: Path,
):
    root, first, _ = _repository(tmp_path)
    unrelated = tmp_path / "unrelated worktree"
    git(root, "worktree", "add", "--detach", str(unrelated), "HEAD")
    (root / "tracked.txt").write_text("caller edit\n")
    (root / "untracked.txt").write_text("caller untracked\n")
    caller_head = git(root, "rev-parse", "HEAD")
    common, owned = _allocate(tmp_path, root, first)

    owned.create()

    assert git(owned.root, "rev-parse", "HEAD") == first
    assert git(owned.root, "branch", "--show-current") == ""
    marker = json.loads(owned.marker.read_text())
    assert set(marker) == {
        "schema",
        "resource_id",
        "work_id",
        "revision",
        "phase",
        "caller_root",
        "caller_identity",
        "common_dir",
        "common_identity",
        "envelope",
        "envelope_identity",
        "checkout",
        "checkout_identity",
    }
    assert marker["phase"] == "ready"
    if os.name != "nt":
        assert stat.S_IMODE(owned.marker.stat().st_mode) == 0o600
        assert stat.S_IMODE(owned.marker.parent.stat().st_mode) == 0o700

    result = owned.cleanup()

    assert result.status == "removed"
    assert result.locator is None
    assert not owned.marker.parent.exists()
    assert unrelated.exists()
    assert git(root, "rev-parse", "HEAD") == caller_head
    assert (root / "tracked.txt").read_text() == "caller edit\n"
    assert (root / "untracked.txt").read_text() == "caller untracked\n"
    assert owned.cleanup().status == "removed"
    assert repository_common_dir(root) == common


@pytest.mark.parametrize("kind", ["tracked", "staged", "untracked", "ignored"])
def test_cleanup_retains_a_dirty_owned_checkout(tmp_path: Path, kind: str):
    root, first, _ = _repository(tmp_path)
    common, owned = _allocate(tmp_path, root, first)
    owned.create()
    if kind == "tracked":
        (owned.root / "tracked.txt").write_text("changed\n")
    elif kind == "staged":
        (owned.root / "tracked.txt").write_text("staged\n")
        git(owned.root, "add", "tracked.txt")
    elif kind == "untracked":
        (owned.root / "new.txt").write_text("new\n")
    else:
        (owned.root / "ignored.log").write_text("ignored\n")

    result = owned.cleanup()

    assert result.status == "recovery-required"
    assert result.locator == str(owned.marker)
    assert "clean" in (result.reason or "").lower()
    assert owned.root.exists()
    assert owned.marker.exists()
    # Recovery is independent of any workflow object.
    assert recover_checkout(marker=owned.marker, common_dir=common).status == "recovery-required"


def test_cleanup_retains_a_checkout_whose_head_changed(tmp_path: Path):
    root, first, second = _repository(tmp_path)
    _, owned = _allocate(tmp_path, root, first)
    owned.create()
    git(owned.root, "reset", "--hard", second)

    result = owned.cleanup()

    assert result.status == "recovery-required"
    assert "revision" in (result.reason or "").lower()
    assert owned.root.exists()


def test_failed_add_before_registration_has_truthful_marker_and_can_be_cleaned(
    tmp_path: Path,
):
    root, _, _ = _repository(tmp_path)
    missing = "0" * 40
    common, owned = _allocate(tmp_path, root, missing)

    with pytest.raises(GitError):
        owned.create()

    assert json.loads(owned.marker.read_text())["phase"] == "creating"
    assert recover_checkout(marker=owned.marker, common_dir=common).status == "removed"
    assert not owned.marker.parent.exists()


def test_allocated_checkout_can_be_cleaned_without_running_git_add(tmp_path: Path):
    root, first, _ = _repository(tmp_path)
    common, owned = _allocate(tmp_path, root, first)

    result = recover_checkout(marker=owned.marker, common_dir=common)

    assert result.status == "removed"
    assert not owned.marker.parent.exists()


def test_failure_after_registration_can_recover_a_clean_creating_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import ai_dlc.work.merge_checkout as lifecycle

    root, first, _ = _repository(tmp_path)
    common, owned = _allocate(tmp_path, root, first)
    real_run_git = lifecycle.run_git

    def run_git(root_arg, *args, **kwargs):
        result = real_run_git(root_arg, *args, **kwargs)
        if args[:3] == ("worktree", "add", "--detach"):
            raise GitError("response lost after registration")
        return result

    monkeypatch.setattr(lifecycle, "run_git", run_git)
    with pytest.raises(GitError, match="response lost"):
        owned.create()

    assert json.loads(owned.marker.read_text())["phase"] == "creating"
    assert recover_checkout(marker=owned.marker, common_dir=common).status == "removed"
    assert not owned.marker.parent.exists()


def test_verification_failure_after_registration_retains_the_owned_resource(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import ai_dlc.work.merge_checkout as lifecycle

    root, first, _ = _repository(tmp_path)
    common, owned = _allocate(tmp_path, root, first)
    real_run_git = lifecycle.run_git

    def run_git(root_arg, *args, **kwargs):
        result = real_run_git(root_arg, *args, **kwargs)
        if args[:3] == ("worktree", "add", "--detach"):
            (owned.root / "ignored.log").write_text("appeared during creation\n")
        return result

    monkeypatch.setattr(lifecycle, "run_git", run_git)
    with pytest.raises(ValueError, match="clean"):
        owned.create()

    assert json.loads(owned.marker.read_text())["phase"] == "creating"
    result = recover_checkout(marker=owned.marker, common_dir=common)
    assert result.status == "recovery-required"
    assert owned.root.exists()


def test_cleanup_refuses_replaced_envelope_identity(tmp_path: Path):
    root, first, _ = _repository(tmp_path)
    _, owned = _allocate(tmp_path, root, first)
    original = owned.marker.parent
    moved = original.with_name(original.name + "-original")
    original.rename(moved)
    original.mkdir(mode=0o700)
    (original / owned.marker.name).write_bytes((moved / owned.marker.name).read_bytes())
    foreign = original / "foreign.txt"
    foreign.write_text("do not remove\n")

    result = owned.cleanup()

    assert result.status == "recovery-required"
    assert foreign.read_text() == "do not remove\n"
    assert original.exists()
    assert moved.exists()


def test_cleanup_does_not_treat_a_missing_renamed_live_envelope_as_removed(
    tmp_path: Path,
):
    root, first, _ = _repository(tmp_path)
    _, owned = _allocate(tmp_path, root, first)
    owned.create()
    moved = owned.marker.parent.with_name(owned.marker.parent.name + "-moved")
    owned.marker.parent.rename(moved)

    result = owned.cleanup()

    assert result.status == "recovery-required"
    assert (moved / "checkout").exists()
    assert (moved / owned.marker.name).exists()
    assert str(owned.root) in git(root, "worktree", "list", "--porcelain")


def test_recovery_retry_removes_checkout_after_user_clears_unexpected_content(
    tmp_path: Path,
):
    root, first, _ = _repository(tmp_path)
    common, owned = _allocate(tmp_path, root, first)
    owned.create()
    unexpected = owned.root / "unexpected.txt"
    unexpected.write_text("inspect first\n")
    assert owned.cleanup().status == "recovery-required"

    unexpected.unlink()
    result = recover_checkout(marker=owned.marker, common_dir=common)

    assert result.status == "removed"
    assert not owned.marker.parent.exists()


def test_recovery_refuses_missing_or_foreign_markers_without_deleting_paths(tmp_path: Path):
    root, _, _ = _repository(tmp_path)
    common = repository_common_dir(root)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    marker = foreign / "ownership.json"
    marker.write_text('{"schema": 1}\n')

    malformed = recover_checkout(marker=marker, common_dir=common)
    missing = recover_checkout(marker=tmp_path / "missing.json", common_dir=common)

    assert malformed.status == "recovery-required"
    assert missing.status == "recovery-required"
    assert marker.exists()
    assert foreign.exists()


def test_cleanup_refuses_a_symlink_replacement(tmp_path: Path):
    root, first, _ = _repository(tmp_path)
    common, owned = _allocate(tmp_path, root, first)
    owned.create()
    git(root, "worktree", "remove", str(owned.root))
    foreign = tmp_path / "foreign directory"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("keep\n")
    try:
        owned.root.symlink_to(foreign, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")

    result = recover_checkout(marker=owned.marker, common_dir=common)

    assert result.status == "recovery-required"
    assert (foreign / "keep.txt").read_text() == "keep\n"
    assert owned.root.is_symlink()


def test_remove_failure_is_reported_without_force_fetch_or_prune(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import ai_dlc.work.merge_checkout as lifecycle

    root, first, _ = _repository(tmp_path)
    _, owned = _allocate(tmp_path, root, first)
    owned.create()
    real_run_git = lifecycle.run_git
    calls: list[tuple[str, ...]] = []

    def run_git(root_arg, *args, **kwargs):
        calls.append(args)
        if args and args[0] == "worktree" and "remove" in args:
            raise GitError("simulated removal failure")
        return real_run_git(root_arg, *args, **kwargs)

    monkeypatch.setattr(lifecycle, "run_git", run_git)
    result = owned.cleanup()

    assert result.status == "recovery-required"
    assert owned.root.exists()
    flattened = {argument for call in calls for argument in call}
    assert "--force" not in flattened
    assert "fetch" not in flattened
    assert "prune" not in flattened


def test_envelope_removal_failure_restores_marker_for_recovery_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root, first, _ = _repository(tmp_path)
    common, owned = _allocate(tmp_path, root, first)
    owned.create()
    envelope = owned.marker.parent
    real_rmdir = Path.rmdir

    def rmdir(path: Path):
        if path == envelope:
            raise OSError("simulated envelope removal failure")
        return real_rmdir(path)

    monkeypatch.setattr(Path, "rmdir", rmdir)
    result = owned.cleanup()

    assert result.status == "recovery-required"
    assert result.locator == str(owned.marker)
    assert owned.marker.exists()
    assert not owned.root.exists()

    monkeypatch.undo()
    assert recover_checkout(marker=owned.marker, common_dir=common).status == "removed"
    assert not envelope.exists()


def test_unexpected_envelope_content_blocks_git_removal(tmp_path: Path):
    root, first, _ = _repository(tmp_path)
    _, owned = _allocate(tmp_path, root, first)
    owned.create()
    sibling = owned.marker.parent / "unexpected.txt"
    sibling.write_text("retain\n")

    result = owned.cleanup()

    assert result.status == "recovery-required"
    assert owned.root.exists()
    assert sibling.read_text() == "retain\n"
