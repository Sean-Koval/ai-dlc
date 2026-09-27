"""Bounded no-follow import and exclusive private publication for safe reports."""

from __future__ import annotations

import os
import secrets
import stat
from contextlib import contextmanager
from pathlib import Path

from ai_dlc.environment.report_schema import MAX_BYTES, parse_report, report_bytes

READ_ERROR = "Effective environment report could not be read safely."
WRITE_ERROR = "Effective environment report could not be written safely."
EXISTS_ERROR = "Effective environment report destination already exists."


class ReportIOError(ValueError):
    """A fixed, path-free report file boundary failure."""


def _absolute(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    if absolute.name in {"", ".", ".."}:
        raise ValueError
    return absolute


@contextmanager
def _open_directory(path: Path):
    """Open every absolute POSIX directory component without following links."""
    absolute = Path(os.path.abspath(path))
    descriptor = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:]:
            next_descriptor = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        yield descriptor
    finally:
        os.close(descriptor)


def _read_posix(path: Path) -> bytes:
    absolute = _absolute(path)
    with _open_directory(absolute.parent) as parent:
        descriptor = os.open(
            absolute.name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent,
        )
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise ValueError
            chunks = bytearray()
            while len(chunks) <= MAX_BYTES:
                chunk = os.read(descriptor, MAX_BYTES + 1 - len(chunks))
                if not chunk:
                    break
                chunks.extend(chunk)
            raw = bytes(chunks)
            if len(raw) > MAX_BYTES:
                raise ValueError
            return raw
        finally:
            os.close(descriptor)


def read_report_bytes(path: Path) -> bytes:
    """Read one bounded regular file without following any selected path link."""
    try:
        if os.name == "nt":
            from ai_dlc._windows_storage import safe_read

            return safe_read(path, max_bytes=MAX_BYTES)
        return _read_posix(path)
    except ReportIOError:
        raise
    except (OSError, ValueError, TypeError):
        raise ReportIOError(READ_ERROR) from None


def read_report(path: Path) -> dict:
    """Read one complete schema-compatible report through a bounded safe path."""
    try:
        return parse_report(read_report_bytes(path))
    except ReportIOError:
        raise
    except (OSError, ValueError, TypeError):
        raise ReportIOError(READ_ERROR) from None


def _write_all(descriptor: int, body: bytes) -> None:
    view = memoryview(body)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError
        view = view[written:]


def _parent_is_current(path: Path, descriptor: int) -> bool:
    expected = os.fstat(descriptor)
    with _open_directory(path) as current:
        actual = os.fstat(current)
    return (actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino)


def _write_posix(path: Path, body: bytes) -> None:
    absolute = _absolute(path)
    with _open_directory(absolute.parent) as parent:
        stage = f".ai-dlc-report-{secrets.token_hex(16)}"
        descriptor = os.open(
            stage,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent,
        )
        try:
            try:
                os.fchmod(descriptor, 0o600)
                _write_all(descriptor, body)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            if not _parent_is_current(absolute.parent, parent):
                raise OSError
            try:
                os.link(
                    stage,
                    absolute.name,
                    src_dir_fd=parent,
                    dst_dir_fd=parent,
                    follow_symlinks=False,
                )
            except FileExistsError:
                raise ReportIOError(EXISTS_ERROR) from None
        finally:
            try:
                os.unlink(stage, dir_fd=parent)
            except FileNotFoundError:
                pass


def write_report(path: Path, report: dict) -> None:
    """Validate completely, then publish a new canonical private report atomically."""
    body = report_bytes(report)
    try:
        if os.name == "nt":
            from ai_dlc._windows_storage import atomic_publish

            created = atomic_publish(path, body, create_only=True, private=True)
            if not created:
                raise ReportIOError(EXISTS_ERROR)
        else:
            _write_posix(path, body)
    except ReportIOError:
        raise
    except (OSError, ValueError, TypeError):
        raise ReportIOError(WRITE_ERROR) from None
