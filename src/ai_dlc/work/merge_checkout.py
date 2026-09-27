"""Owned detached checkout lifecycle for exact-merge finish evidence."""

from __future__ import annotations

import json
import os
import re
import stat
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ai_dlc.files import atomic_create, atomic_write, run_git

_REVISION = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
_RESOURCE = re.compile(r"[0-9a-f]{32}\Z")
_MARKER_NAME = "ownership.json"
_MARKER_FIELDS = {
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
_Identity = tuple[int, ...]


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _posix_chain(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Snapshot every component without resolving symlinks away."""
    path = _absolute(path)
    current = Path(path.anchor)
    result: list[tuple[str, int, int]] = []
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except OSError:
            raise ValueError(f"Managed path identity is unavailable: {current}") from None
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"Managed path contains a symlink: {current}")
        result.append((part, metadata.st_dev, metadata.st_ino))
    return tuple(result)


def _directory_identity(path: Path, *, private: bool = False) -> _Identity:
    path = _absolute(path)
    if os.name == "nt":
        from ai_dlc._windows_storage import guarded_path

        with guarded_path(path, private=private):
            metadata = path.stat()
    else:
        before = _posix_chain(path)
        metadata = path.lstat()
        after = _posix_chain(path)
        if before != after:
            raise ValueError(f"Managed path identity changed during validation: {path}")
        if private and (metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077):
            raise ValueError(f"Managed directory must be private: {path}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"Managed path is not a directory: {path}")
    return (metadata.st_dev, metadata.st_ino)


def _identity_value(value: Any, *, nullable: bool = False) -> _Identity | None:
    if nullable and value is None:
        return None
    if (
        not isinstance(value, list)
        or len(value) < 2
        or any(type(item) is not int for item in value)
    ):
        raise ValueError("Owned checkout marker contains an invalid filesystem identity")
    return tuple(value)


def _create_private_directory(path: Path, *, parents: bool = False) -> _Identity:
    path = _absolute(path)
    if os.name == "nt":
        from ai_dlc._windows_storage import guarded_path

        existed = path.exists() or path.is_symlink()
        if not parents:
            with guarded_path(path.parent):
                pass
        with guarded_path(path, create_parents=True, private=True):
            pass
        if existed and not parents:
            raise FileExistsError(f"Managed destination already exists: {path}")
        return _directory_identity(path, private=True)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    cloexec = getattr(os, "O_CLOEXEC", 0)
    flags = os.O_RDONLY | os.O_DIRECTORY | nofollow | cloexec
    descriptor = os.open(path.anchor, flags)
    try:
        for index, part in enumerate(path.parts[1:]):
            final = index == len(path.parts[1:]) - 1
            created = False
            try:
                child = os.open(part, flags, dir_fd=descriptor)
            except FileNotFoundError:
                if not parents and not final:
                    raise ValueError(
                        f"Managed parent directory is unavailable: {path.parent}"
                    ) from None
                os.mkdir(part, mode=0o700, dir_fd=descriptor)
                created = True
                child = os.open(part, flags, dir_fd=descriptor)
            except OSError:
                raise ValueError(
                    f"Managed directory contains a symlink or unsafe path: {path}"
                ) from None
            os.close(descriptor)
            descriptor = child
            if final and not parents and not created:
                raise FileExistsError(f"Managed destination already exists: {path}")
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            raise ValueError(f"Managed directory must be private: {path}")
        identity = (metadata.st_dev, metadata.st_ino)
    finally:
        os.close(descriptor)
    if _directory_identity(path, private=True) != identity:
        raise ValueError(f"Managed directory identity changed during creation: {path}")
    return identity


def _discard_empty_envelope(envelope: Path, identity: _Identity) -> None:
    if _directory_identity(envelope, private=True) != identity or any(envelope.iterdir()):
        raise ValueError("Allocated checkout envelope changed before rollback")
    envelope.rmdir()


def _filesystem_path_output(value: bytes) -> tuple[str, bytes]:
    raw = value[:-1] if value.endswith(b"\n") else value
    raw = raw[:-1] if raw.endswith(b"\r") else raw
    if not raw or any(separator in raw for separator in (b"\0", b"\r", b"\n")):
        raise ValueError("Git returned an ambiguous common-directory path")
    return os.fsdecode(raw), raw


def _path_diagnostic(value: str | bytes) -> str:
    bounded = value[:1024]
    suffix = "" if len(value) <= len(bounded) else f"... ({len(value)} units total)"
    return f"{bounded!a}{suffix}"


def repository_common_dir(root: Path) -> Path:
    """Return the guarded absolute common Git directory for a checkout."""
    root = _absolute(root)
    root_before = _directory_identity(root)
    result = run_git(
        root,
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
        text=False,
        context="Cannot resolve the repository common Git directory",
    )
    value, raw = _filesystem_path_output(result.stdout)
    common = Path(value)
    if not common.is_absolute():
        raise ValueError("Git returned an ambiguous common-directory identity")
    common = _absolute(common)
    try:
        common_before = _directory_identity(common)
    except (OSError, ValueError) as error:
        error.add_note(
            f"Caller root was {_path_diagnostic(str(root))}; Git common-directory bytes were "
            f"{_path_diagnostic(raw)}; filesystem decoding produced {_path_diagnostic(value)}"
        )
        raise
    if _directory_identity(root) != root_before or _directory_identity(common) != common_before:
        raise ValueError("Repository identity changed while resolving its common Git directory")
    repeated, _ = _filesystem_path_output(
        run_git(
            root,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
            text=False,
            context="Cannot verify the repository common Git directory",
        ).stdout
    )
    if _absolute(Path(repeated)) != common:
        raise ValueError("Repository common-directory identity changed during validation")
    return common


def _missing_revision(revision: str, repository: str) -> ValueError:
    return ValueError(
        f"Merged revision {revision} is not an exact local commit for trusted repository "
        f"{repository}; fetch that exact object from {repository} (for example, "
        f"`git fetch {repository} {revision}`) and retry"
    )


def require_merge_commit(root: Path, revision: str, repository: str) -> None:
    """Require a full object ID that peels to that same commit, without fetching."""
    if not _REVISION.fullmatch(revision):
        raise _missing_revision(revision, repository)
    result = run_git(
        root,
        "rev-parse",
        "--verify",
        f"{revision.lower()}^{{commit}}",
        check=False,
        context="Cannot inspect the merged revision",
    )
    if result.returncode or result.stdout.strip().lower() != revision.lower():
        raise _missing_revision(revision, repository)


@dataclass(frozen=True)
class CleanupResult:
    status: Literal["removed", "recovery-required"]
    locator: str | None = None
    reason: str | None = None
    remedy: str | None = None


@dataclass(frozen=True)
class OwnedMergeCheckout:
    root: Path
    revision: str
    marker: Path
    _resource_id: str = field(repr=False)
    _work_id: str = field(repr=False)
    _caller_root: Path = field(repr=False)
    _caller_identity: _Identity = field(repr=False)
    _common_dir: Path = field(repr=False)
    _common_identity: _Identity = field(repr=False)
    _envelope_identity: _Identity = field(repr=False)
    _verified_removed: bool = field(default=False, init=False, repr=False, compare=False)

    def create(self) -> None:
        document, _, _ = _validated_marker(self.marker, self._common_dir, expected=self)
        if document["phase"] != "allocated":
            raise ValueError("Owned merge checkout is not in its allocated phase")
        if _directory_identity(self._caller_root) != self._caller_identity:
            raise ValueError("Caller checkout identity changed before worktree creation")
        if _directory_identity(self._common_dir) != self._common_identity:
            raise ValueError("Common Git directory identity changed before worktree creation")
        document["phase"] = "creating"
        _replace_marker(self.marker, document, self._envelope_identity)
        run_git(
            self._caller_root,
            "worktree",
            "add",
            "--detach",
            str(self.root),
            self.revision,
            context="Cannot create the owned merge checkout",
        )
        checkout_identity = _directory_identity(self.root)
        _validate_live_checkout(
            root=self.root,
            revision=self.revision,
            common_dir=self._common_dir,
            common_identity=self._common_identity,
            recorded_identity=None,
        )
        document["checkout_identity"] = list(checkout_identity)
        document["phase"] = "ready"
        _replace_marker(self.marker, document, self._envelope_identity)

    def cleanup(self) -> CleanupResult:
        if self._verified_removed:
            return CleanupResult(status="removed")
        result = _cleanup(self.marker, self._common_dir, expected=self)
        if result.status == "removed":
            object.__setattr__(self, "_verified_removed", True)
        return result


def allocate_checkout(
    *, caller_root: Path, common_dir: Path, state_dir: Path, work_id: str, revision: str
) -> OwnedMergeCheckout:
    """Allocate a private ownership envelope without running Git worktree add."""
    if not work_id or not isinstance(work_id, str):
        raise ValueError("Owned merge checkout requires a work ID")
    if not _REVISION.fullmatch(revision):
        raise ValueError("Owned merge checkout requires a full hexadecimal revision")
    caller_root = _absolute(caller_root)
    common_dir = _absolute(common_dir)
    state_dir = _absolute(state_dir)
    actual_common = repository_common_dir(caller_root)
    if actual_common != common_dir:
        raise ValueError("Caller repository does not match the selected common Git directory")
    caller_identity = _directory_identity(caller_root)
    common_identity = _directory_identity(common_dir)
    namespace = state_dir / "merge-checkouts"
    _create_private_directory(namespace, parents=True)
    resource_id = uuid.uuid4().hex
    envelope = namespace / resource_id
    envelope_identity = _create_private_directory(envelope)
    root = envelope / "checkout"
    marker = envelope / _MARKER_NAME
    document = {
        "schema": 1,
        "resource_id": resource_id,
        "work_id": work_id,
        "revision": revision.lower(),
        "phase": "allocated",
        "caller_root": str(caller_root),
        "caller_identity": list(caller_identity),
        "common_dir": str(common_dir),
        "common_identity": list(common_identity),
        "envelope": str(envelope),
        "envelope_identity": list(envelope_identity),
        "checkout": str(root),
        "checkout_identity": None,
    }
    data = json.dumps(document, sort_keys=True, indent=2) + "\n"
    try:
        created = atomic_create(marker, data, 0o600)
    except Exception as error:
        try:
            _discard_empty_envelope(envelope, envelope_identity)
        except Exception as cleanup_error:  # noqa: BLE001
            error.add_note(f"Allocated envelope requires recovery: {cleanup_error}")
        raise
    if not created:
        _discard_empty_envelope(envelope, envelope_identity)
        raise ValueError("Owned merge checkout marker already exists")
    return OwnedMergeCheckout(
        root=root,
        revision=revision.lower(),
        marker=marker,
        _resource_id=resource_id,
        _work_id=work_id,
        _caller_root=caller_root,
        _caller_identity=caller_identity,
        _common_dir=common_dir,
        _common_identity=common_identity,
        _envelope_identity=envelope_identity,
    )


def recover_checkout(*, marker: Path, common_dir: Path) -> CleanupResult:
    """Retry local cleanup from an ownership marker without opening workflow services."""
    return _cleanup(_absolute(marker), _absolute(common_dir), expected=None)


def _marker_snapshot(marker: Path) -> tuple[bytes, _Identity]:
    marker = _absolute(marker)
    if os.name == "nt":
        from ai_dlc._windows_storage import safe_snapshot

        data, identity = safe_snapshot(marker, max_bytes=32 * 1024, private=True)
        return data, tuple(identity)
    _posix_chain(marker)
    linked = marker.lstat()
    if (
        not stat.S_ISREG(linked.st_mode)
        or linked.st_uid != os.getuid()
        or stat.S_IMODE(linked.st_mode) & 0o077
        or linked.st_nlink != 1
        or linked.st_size > 32 * 1024
    ):
        raise ValueError("Owned checkout marker must be a private regular single-link file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(marker, flags)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (linked.st_dev, linked.st_ino):
            raise ValueError("Owned checkout marker identity changed while reading")
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                raise ValueError("Owned checkout marker changed while reading")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks), (opened.st_dev, opened.st_ino)
    finally:
        os.close(descriptor)


def _validated_marker(
    marker: Path,
    common_dir: Path,
    *,
    expected: OwnedMergeCheckout | None,
) -> tuple[dict[str, Any], bytes, _Identity]:
    marker = _absolute(marker)
    common_dir = _absolute(common_dir)
    data, marker_identity = _marker_snapshot(marker)
    try:
        document = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Owned checkout marker is unreadable") from None
    if not isinstance(document, dict) or set(document) != _MARKER_FIELDS:
        raise ValueError("Owned checkout marker has an unsupported schema")
    if document["schema"] != 1:
        raise ValueError("Owned checkout marker has an unsupported schema")
    required_strings = (
        "resource_id",
        "work_id",
        "revision",
        "phase",
        "caller_root",
        "common_dir",
        "envelope",
        "checkout",
    )
    if any(not isinstance(document[key], str) or not document[key] for key in required_strings):
        raise ValueError("Owned checkout marker contains an invalid field")
    if (
        not _RESOURCE.fullmatch(document["resource_id"])
        or not _REVISION.fullmatch(document["revision"])
        or document["phase"] not in {"allocated", "creating", "ready"}
    ):
        raise ValueError("Owned checkout marker contains an invalid identity or phase")
    caller = Path(document["caller_root"])
    recorded_common = Path(document["common_dir"])
    envelope = Path(document["envelope"])
    checkout = Path(document["checkout"])
    if not all(path.is_absolute() for path in (caller, recorded_common, envelope, checkout)):
        raise ValueError("Owned checkout marker contains a relative path")
    if (
        marker != envelope / _MARKER_NAME
        or envelope.name != document["resource_id"]
        or envelope.parent.name != "merge-checkouts"
        or checkout != envelope / "checkout"
        or recorded_common != common_dir
    ):
        raise ValueError("Owned checkout marker does not own the requested path")
    caller_identity = _identity_value(document["caller_identity"])
    common_identity = _identity_value(document["common_identity"])
    envelope_identity = _identity_value(document["envelope_identity"])
    _identity_value(document["checkout_identity"], nullable=True)
    assert caller_identity is not None
    assert common_identity is not None
    assert envelope_identity is not None
    if _directory_identity(envelope, private=True) != envelope_identity:
        raise ValueError("Owned checkout envelope identity was replaced")
    if _directory_identity(common_dir) != common_identity:
        raise ValueError("Common Git directory identity was replaced")
    if expected is not None and (
        document["resource_id"] != expected._resource_id
        or document["work_id"] != expected._work_id
        or document["revision"].lower() != expected.revision
        or caller != expected._caller_root
        or caller_identity != expected._caller_identity
        or common_identity != expected._common_identity
        or envelope_identity != expected._envelope_identity
        or marker != expected.marker
        or checkout != expected.root
    ):
        raise ValueError("Owned checkout marker does not match its allocated resource")
    return document, data, marker_identity


def _replace_marker(marker: Path, document: dict[str, Any], envelope_identity: _Identity) -> None:
    if _directory_identity(marker.parent, private=True) != envelope_identity:
        raise ValueError("Owned checkout envelope changed before marker update")
    _marker_snapshot(marker)
    atomic_write(marker, json.dumps(document, sort_keys=True, indent=2) + "\n", mode=0o600)


def _registrations(common_dir: Path) -> dict[Path, dict[str, str | bool]]:
    result = run_git(
        common_dir,
        "worktree",
        "list",
        "--porcelain",
        "-z",
        context="Cannot inspect owned worktree registration",
    )
    registrations: dict[Path, dict[str, str | bool]] = {}
    for block in result.stdout.split("\0\0"):
        if not block:
            continue
        fields = [value for value in block.split("\0") if value]
        if not fields or not fields[0].startswith("worktree "):
            raise ValueError("Git returned an ambiguous worktree registration")
        path = _absolute(Path(fields[0][len("worktree ") :]))
        entry: dict[str, str | bool] = {}
        for value in fields[1:]:
            key, _, item = value.partition(" ")
            entry[key] = item if item else True
        registrations[path] = entry
    return registrations


def _dirty(root: Path) -> bool:
    result = run_git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=matching",
        context="Cannot inspect owned merge checkout cleanliness",
    )
    return bool(result.stdout)


def _validate_live_checkout(
    *,
    root: Path,
    revision: str,
    common_dir: Path,
    common_identity: _Identity,
    recorded_identity: _Identity | None,
) -> None:
    identity = _directory_identity(root)
    if recorded_identity is not None and identity != recorded_identity:
        raise ValueError("Owned checkout filesystem identity was replaced")
    if (
        repository_common_dir(root) != common_dir
        or _directory_identity(common_dir) != common_identity
    ):
        raise ValueError("Owned checkout is registered in a different repository")
    registration = _registrations(common_dir).get(root)
    if registration is None:
        raise ValueError("Owned checkout is not registered in the common Git directory")
    head = run_git(root, "rev-parse", "--verify", "HEAD", context="Cannot inspect checkout HEAD")
    if head.stdout.strip().lower() != revision.lower():
        raise ValueError("Owned checkout revision changed; recovery is required")
    symbolic = run_git(root, "symbolic-ref", "-q", "HEAD", check=False)
    if symbolic.returncode == 0 or registration.get("detached") is not True:
        raise ValueError("Owned checkout is no longer detached")
    if str(registration.get("HEAD", "")).lower() != revision.lower():
        raise ValueError("Owned checkout registration revision changed")
    if _dirty(root):
        raise ValueError("Owned checkout is not clean; recovery is required")


def _recovery(marker: Path, checkout: Path | None, reason: str) -> CleanupResult:
    retained = checkout if checkout is not None and checkout.exists() else marker
    if checkout is None:
        remedy = (
            f"Inspect marker {marker}; do not remove any referenced path until its ownership "
            "and contents have been verified."
        )
    else:
        remedy = (
            f"Inspect the retained resource at {retained} and marker {marker}. If the checkout "
            "is unchanged and still registered, remove it manually with nonforced "
            f"`git worktree remove {checkout}`; then remove the verified marker and empty envelope."
        )
    return CleanupResult(
        status="recovery-required",
        locator=str(marker),
        reason=reason,
        remedy=remedy,
    )


def _delete_empty_envelope(
    marker: Path,
    document: dict[str, Any],
    marker_data: bytes,
    marker_identity: _Identity,
) -> None:
    envelope = marker.parent
    entries = list(envelope.iterdir())
    if entries != [marker]:
        raise ValueError("Owned checkout envelope contains unexpected paths")
    expected_envelope = _identity_value(document["envelope_identity"])
    if _directory_identity(envelope, private=True) != expected_envelope:
        raise ValueError("Owned checkout envelope changed before removal")
    if os.name == "nt":
        from ai_dlc._windows_storage import conditional_remove

        if not conditional_remove(
            marker,
            expected=marker_data,
            expected_identity=marker_identity,  # type: ignore[arg-type]
        ):
            raise ValueError("Owned checkout marker changed before removal")
    else:
        linked = marker.lstat()
        if (linked.st_dev, linked.st_ino) != marker_identity:
            raise ValueError("Owned checkout marker changed before removal")
        marker.unlink()
    try:
        if _directory_identity(envelope, private=True) != expected_envelope:
            raise ValueError("Owned checkout envelope changed before removal")
        envelope.rmdir()
    except BaseException as error:
        try:
            if _directory_identity(envelope, private=True) != expected_envelope:
                raise ValueError("Owned checkout envelope was replaced after marker removal")
            if marker.exists() or marker.is_symlink():
                raise ValueError("Owned checkout marker path changed after removal")
            if not atomic_create(marker, marker_data.decode("utf-8"), 0o600):
                raise ValueError("Owned checkout marker path was occupied during recovery")
            restored, _ = _marker_snapshot(marker)
            if restored != marker_data:
                raise ValueError("Restored ownership marker does not match verified metadata")
        except Exception as restore_error:  # noqa: BLE001
            error.add_note(f"Ownership marker could not be restored safely: {restore_error}")
        raise


def _cleanup(
    marker: Path,
    common_dir: Path,
    *,
    expected: OwnedMergeCheckout | None,
) -> CleanupResult:
    checkout: Path | None = expected.root if expected is not None else None
    try:
        document, marker_data, marker_identity = _validated_marker(
            marker, common_dir, expected=expected
        )
        checkout = Path(document["checkout"])
        registrations = _registrations(common_dir)
        registration = registrations.get(checkout)
        exists = checkout.exists() or checkout.is_symlink()
        if not exists and registration is None:
            _delete_empty_envelope(marker, document, marker_data, marker_identity)
            return CleanupResult(status="removed")
        if not exists or registration is None:
            raise ValueError("Owned checkout path and Git registration disagree")
        recorded_identity = _identity_value(document["checkout_identity"], nullable=True)
        common_identity = _identity_value(document["common_identity"])
        assert common_identity is not None
        _validate_live_checkout(
            root=checkout,
            revision=document["revision"],
            common_dir=common_dir,
            common_identity=common_identity,
            recorded_identity=recorded_identity,
        )
        entries = set(marker.parent.iterdir())
        if entries != {marker, checkout}:
            raise ValueError("Owned checkout envelope contains unexpected paths")
        run_git(
            common_dir,
            "worktree",
            "remove",
            str(checkout),
            context="Cannot remove the owned merge checkout without force",
        )
        if checkout.exists() or checkout.is_symlink() or checkout in _registrations(common_dir):
            raise ValueError("Git did not fully remove the owned merge checkout")
        document, marker_data, marker_identity = _validated_marker(
            marker, common_dir, expected=expected
        )
        _delete_empty_envelope(marker, document, marker_data, marker_identity)
        return CleanupResult(status="removed")
    # Cleanup is a best-effort result boundary: filesystem and Git refusals must not
    # replace an already known finish outcome in the caller.
    except Exception as error:  # noqa: BLE001
        return _recovery(marker, checkout, str(error))
