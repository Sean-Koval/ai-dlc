"""No-follow, descriptor-relative access for explicitly selected document trees."""

import hashlib
import os
import stat
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def directory(path: Path, *, create: bool = False):
    """Open each component without following links; descriptors pin opened directories."""
    if os.name == "nt":
        raise ValueError("Descriptor-based document traversal is not supported on native Windows")
    absolute = Path(os.path.abspath(path))
    fd = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:]:
            if create:
                try:
                    os.mkdir(part, dir_fd=fd)
                except FileExistsError:
                    pass
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        yield fd
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ValueError(f"Document directory unavailable or unsafe: {path}") from exc
    finally:
        os.close(fd)


def read_document(path: Path) -> bytes:
    if os.name == "nt":
        from ai_dlc._windows_storage import safe_read

        return safe_read(path)
    with directory(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError(f"Document is not a regular file: {path}")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                return stream.read()
        finally:
            os.close(fd)


def read_bounded(root: Path, relative: str, remaining: int) -> dict:
    """Read one complete UTF-8 body within a byte budget; oversized bodies stay unread."""
    path = root / relative
    if os.name == "nt":
        from ai_dlc._windows_storage import safe_read

        raw = safe_read(path, max_bytes=remaining)
        return _bounded_result(relative, raw)
    with directory(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("not a regular file")
            if info.st_size > remaining:
                raise ValueError("body budget exceeded; content not read")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(remaining + 1)
            if len(raw) > remaining:
                raise ValueError("body budget exceeded")
            return _bounded_result(relative, raw)
        finally:
            os.close(fd)


def _bounded_result(relative: str, raw: bytes) -> dict:
    text = raw.decode("utf-8")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
        raise ValueError("binary content")
    return {
        "path": relative,
        "content": text,
        "digest": hashlib.sha256(raw).hexdigest(),
        "start_line": 1,
        "end_line": len(text.splitlines()),
    }


def create_document(path: Path, body: bytes) -> bool:
    """Exclusive create, no replacement or pathname cleanup; safe retry preserves output."""
    if os.name == "nt":
        from ai_dlc._windows_storage import atomic_publish

        return atomic_publish(path, body, create_only=True)
    with directory(path.parent, create=True) as parent:
        try:
            fd = os.open(
                path.name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o644,
                dir_fd=parent,
            )
        except FileExistsError:
            return False
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        return True


def validate_parent(path: Path) -> None:
    """Apply publication's no-follow rules to existing parents without creating missing ones."""
    try:
        if os.name == "nt":
            from ai_dlc._windows_storage import guarded_path

            with guarded_path(path.parent):
                pass
        else:
            with directory(path.parent):
                pass
    except FileNotFoundError:
        pass
