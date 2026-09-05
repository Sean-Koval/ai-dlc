"""Cross-process coordination for project-owned writes."""

from __future__ import annotations

import fcntl
import hashlib
import os
import stat
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_PROCESS_LOCK = threading.RLock()
_LOCAL = threading.local()
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_CLOEXEC = getattr(os, "O_CLOEXEC", 0)


def _invalid_namespace() -> ValueError:
    return ValueError("AI-DLC project lock namespace must be private and symlink-free")


def _validate_directory(metadata: os.stat_result) -> None:
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        raise _invalid_namespace()


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            if current.is_symlink():
                raise _invalid_namespace()
        except OSError:
            raise _invalid_namespace() from None


def _open_anchor(path: Path) -> int:
    path = Path(os.path.abspath(path))
    _reject_symlink_components(path)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        parent = path.parent
        try:
            parent_metadata = parent.lstat()
        except OSError:
            raise _invalid_namespace() from None
        _validate_directory(parent_metadata)
        if parent.is_symlink():
            raise _invalid_namespace()
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass
        metadata = path.lstat()
    except OSError:
        raise _invalid_namespace() from None
    if path.is_symlink():
        raise _invalid_namespace()
    _validate_directory(metadata)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | _NOFOLLOW | _CLOEXEC)
    except OSError:
        raise _invalid_namespace() from None
    opened = os.fstat(descriptor)
    try:
        _validate_directory(opened)
        if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise _invalid_namespace()
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _open_private_child(parent: int, name: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | _NOFOLLOW | _CLOEXEC
    try:
        descriptor = os.open(name, flags, dir_fd=parent)
    except FileNotFoundError:
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            pass
        try:
            descriptor = os.open(name, flags, dir_fd=parent)
        except OSError:
            raise _invalid_namespace() from None
    except OSError:
        raise _invalid_namespace() from None
    try:
        _validate_directory(os.fstat(descriptor))
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


@contextmanager
def _lock_namespace() -> Iterator[int]:
    configured = os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("XDG_CACHE_HOME")
    if configured and not Path(configured).is_absolute():
        raise _invalid_namespace()
    anchor = Path(configured) if configured else Path.home() / ".cache"
    descriptor = _open_anchor(anchor)
    try:
        for name in ("ai-dlc", "locks"):
            child = _open_private_child(descriptor, name)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def _locked_project_file(key: str) -> Iterator[None]:
    flags = os.O_RDWR | os.O_CREAT | _NOFOLLOW | _CLOEXEC
    with _lock_namespace() as namespace:
        try:
            descriptor = os.open(f"{key}.lock", flags, 0o600, dir_fd=namespace)
        except OSError:
            raise _invalid_namespace() from None
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077
                or metadata.st_nlink != 1
            ):
                raise _invalid_namespace()
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            linked = os.stat(f"{key}.lock", dir_fd=namespace, follow_symlinks=False)
            if (linked.st_dev, linked.st_ino) != (metadata.st_dev, metadata.st_ino):
                raise _invalid_namespace()
            try:
                yield
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


@contextmanager
def project_write_lock(root: Path) -> Iterator[None]:
    """Serialize AI-DLC writes for one project, with same-thread reentrancy."""
    resolved = Path(root).resolve()
    key = hashlib.sha256(str(resolved).encode()).hexdigest()
    depths = getattr(_LOCAL, "depths", None)
    if depths is None:
        depths = {}
        _LOCAL.depths = depths

    with _PROCESS_LOCK:
        if depths.get(key, 0):
            depths[key] += 1
            try:
                yield
            finally:
                depths[key] -= 1
            return

        with _locked_project_file(key):
            depths[key] = 1
            try:
                yield
            finally:
                depths.pop(key, None)
