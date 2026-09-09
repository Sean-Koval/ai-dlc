"""No-follow, descriptor-relative access for explicitly selected document trees."""

import os
import stat
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def directory(path: Path, *, create: bool = False):
    """Open each component without following links; descriptors pin opened directories."""
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
    with directory(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError(f"Document is not a regular file: {path}")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                return stream.read()
        finally:
            os.close(fd)


def create_document(path: Path, body: bytes) -> bool:
    """Exclusive create, no replacement or pathname cleanup; safe retry preserves output."""
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
        with directory(path.parent):
            pass
    except FileNotFoundError:
        pass
