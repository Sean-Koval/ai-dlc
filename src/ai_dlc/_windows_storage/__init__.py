"""Private local-NTFS primitives; no silent fallback to unsafe pathname operations.

Directory handles deny delete sharing for the whole operation. Owned moves and
removals operate on a verified open file handle, never on a later pathname occupant.
Atomic replacement is deliberately not a compare-and-swap API: ownership-sensitive
multi-file callers capture old files with move_owned, then publish create-only.
"""

from __future__ import annotations

import ctypes as c
import os
import uuid
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager, nullcontext
from ctypes import wintypes as w
from pathlib import Path, PureWindowsPath

from ._api import IoStatus, Overlapped, RenameInfo, api, checked, info, open_relative, winerror
from ._security import copied_attributes, local_app_data, private_attributes, validate_private

_READ = 0x80000000
_WRITE = 0x40000000
_DELETE = 0x10000
_CONTROL = 0x20000
_REPARSE = 0x400
_DIRECTORY = 0x10


def validate_relative(relative: str) -> None:
    path = PureWindowsPath(relative)
    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    reserved.update(f"{prefix}{number}" for prefix in ("COM", "LPT") for number in "123456789¹²³")
    if (
        not relative
        or path.drive
        or path.root
        or any(
            part in {".", ".."}
            or part.endswith((".", " "))
            or any(ord(char) < 32 or char in '<>:"|?*' for char in part)
            or part.split(".", 1)[0].upper() in reserved
            for part in path.parts
        )
    ):
        raise ValueError(f"Unsafe managed Windows relative path: {relative}")


def _absolute(path: Path) -> Path:
    raw = PureWindowsPath(str(path))
    if raw.drive.startswith("\\") or (raw.drive and not raw.root) or ".." in raw.parts:
        raise ValueError("Native managed storage requires an absolute local NTFS path")
    absolute = Path(os.path.abspath(path))
    if not absolute.drive or absolute.drive.startswith("\\"):
        raise ValueError("Native managed storage requires an absolute local NTFS path")
    for part in absolute.parts[1:]:
        validate_relative(part)
    return absolute


@contextmanager
def opened(
    path: Path,
    *,
    access: int = _READ | _CONTROL,
    share: int = 1,
    creation: int = 3,
    attributes=None,
    parent=None,
    directory: bool = False,
):
    if parent is not None:
        if info(parent).attributes & _REPARSE:
            raise ValueError("Native managed parent became a reparse point")
        handle = open_relative(parent, path.name, access, share, creation, attributes, directory)
    else:
        handle = api().open(
            str(path), access, share, attributes, creation, 0x02000000 | 0x00200000, None
        )
        if handle == c.c_void_p(-1).value:
            raise winerror()
    try:
        if info(handle).attributes & _REPARSE:
            raise ValueError(f"Native managed path is a reparse point: {path}")
        yield handle
    finally:
        api().close(handle)


def _ntfs(handle, path: Path) -> None:
    filesystem = c.create_unicode_buffer(32)
    checked(api().volume(handle, None, 0, None, None, None, filesystem, len(filesystem)))
    if filesystem.value.upper() != "NTFS" or api().drive(path.anchor) != 3:
        raise ValueError("Native managed storage supports local fixed NTFS volumes only")


@contextmanager
def guarded_path(
    path: Path, *, create_parents: bool = False, private: bool = False
) -> Iterator[int]:
    """Hold every directory component against reparse/rename until the caller exits."""
    path = _absolute(path)
    with ExitStack() as stack:
        current = Path(path.anchor)
        # FILE_LIST_DIRECTORY engages sharing checks; metadata-only handles do not.
        # Keep write sharing for the kernel's rename-target directory open, while
        # denying deletion/rename of every held ancestor. Relative handles, not
        # write sharing, prevent attribute-only reparse-point redirection.
        handle = stack.enter_context(opened(current, access=0x81 | _CONTROL, share=3))
        _ntfs(handle, current)
        for part in path.parts[1:]:
            current /= part
            with (
                private_attributes()
                if private and create_parents
                else nullcontext(None) as attributes
            ):
                handle = stack.enter_context(
                    opened(
                        current,
                        access=0x81 | _CONTROL,
                        share=3,
                        parent=handle,
                        directory=True,
                        creation=4 if create_parents else 3,
                        attributes=attributes,
                    )
                )
            if not info(handle).attributes & _DIRECTORY:
                raise ValueError(f"Managed ancestor is not a directory: {current}")
        if private:
            validate_private(handle)
        yield handle


def _read_handle(handle, max_bytes: int | None = None) -> bytes:
    metadata = info(handle)
    if metadata.attributes & _DIRECTORY:
        raise ValueError("Managed content must be a regular file")
    size = (metadata.size_high << 32) | metadata.size_low
    if max_bytes is not None and size > max_bytes:
        raise ValueError(f"Managed file exceeds read budget of {max_bytes} bytes")
    chunks = []
    remaining = size
    while remaining:
        buffer = c.create_string_buffer(min(remaining, 1024 * 1024))
        count = w.DWORD()
        checked(api().read(handle, buffer, len(buffer), c.byref(count), None))
        if not count.value:
            raise OSError("Managed file changed during bounded read")
        chunks.append(buffer.raw[: count.value])
        remaining -= count.value
    return b"".join(chunks)


def safe_snapshot(
    path: Path, *, max_bytes: int | None = None, private: bool = False
) -> tuple[bytes, tuple[int, int, int]]:
    path = _absolute(path)
    with guarded_path(path.parent) as parent, opened(path, parent=parent) as handle:
        if private:
            validate_private(handle)
        return _read_handle(handle, max_bytes), info(handle).identity


def safe_read(path: Path, *, max_bytes: int | None = None, private: bool = False) -> bytes:
    return safe_snapshot(path, max_bytes=max_bytes, private=private)[0]


def _rename(handle, destination: Path, *, parent, replace: bool = False) -> None:
    if info(parent).attributes & _REPARSE:
        raise ValueError("Native publication parent became a reparse point")
    encoded = destination.name.encode("utf-16-le")
    # Native FILE_RENAME_INFORMATION requires the structure plus filename bytes.
    buffer = c.create_string_buffer(c.sizeof(RenameInfo) + len(encoded) + 2)
    header = RenameInfo.from_buffer(buffer)
    header.replace = replace
    header.root = parent
    header.length = len(encoded)
    c.memmove(c.addressof(buffer) + RenameInfo.name.offset, encoded, len(encoded))
    status = IoStatus()
    # The Win32 wrapper rejects relative RootDirectory publication on supported
    # native runners. NtSetInformationFile accepts the same handle-bound rename
    # data directly; never fall back to resolving an absolute destination path.
    result = api().nt_set_info(handle, c.byref(status), buffer, len(buffer), 10)
    if result < 0:
        error = winerror(api().nt_error(result))
        error.add_note(f"Native rename failed with NTSTATUS 0x{result & 0xFFFFFFFF:08X}")
        raise error


def _remove(handle) -> None:
    disposition = w.BOOL(True)
    checked(api().set_info(handle, 4, c.byref(disposition), c.sizeof(disposition)))


def _write_handle(handle, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        chunk = data[offset : offset + 1024 * 1024]
        count = w.DWORD()
        checked(api().write(handle, chunk, len(chunk), c.byref(count), None))
        if not count.value:
            raise OSError("Native stage write made no progress")
        offset += count.value
    checked(api().flush(handle))


def _publish(
    path: Path,
    data: bytes,
    *,
    create_only: bool = False,
    private: bool = False,
    security_attributes=None,
) -> tuple[int, int, int] | None:
    """Atomically publish complete bytes. Use move_owned for ownership-aware updates."""
    path = _absolute(path)
    with guarded_path(path.parent, create_parents=True) as parent, ExitStack() as stack:
        attributes = security_attributes
        try:
            with opened(path, parent=parent) as existing:
                if info(existing).attributes & _DIRECTORY:
                    raise ValueError("Cannot publish over a directory")
                if create_only:
                    # Existing content is not ours to modify or reclassify. A
                    # false creation result makes no claim about its privacy.
                    return None
                if private:
                    validate_private(existing)
                if not private:
                    attributes = stack.enter_context(copied_attributes(existing))
        except FileNotFoundError:
            pass
        if private:
            attributes = stack.enter_context(private_attributes())
        stage = path.with_name(f".ai-dlc-{uuid.uuid4().hex}")
        with opened(
            stage,
            access=_READ | _WRITE | _DELETE | _CONTROL,
            creation=1,
            attributes=attributes,
            parent=parent,
        ) as handle:
            try:
                _write_handle(handle, data)
                if private:
                    validate_private(handle)
                identity = info(handle).identity
                _rename(handle, path, parent=parent, replace=not create_only)
            except OSError as error:
                # Delete exactly our open stage, never a replacement at its name.
                _remove(handle)
                if create_only and getattr(error, "winerror", None) in {80, 183}:
                    return None
                error.add_note(
                    f"Native publication failed for {path}; previous destination is preserved; close conflicting handles and retry"
                )
                raise
            except BaseException:
                _remove(handle)
                raise
    return identity


def atomic_publish(
    path: Path, data: bytes, *, create_only: bool = False, private: bool = False
) -> bool:
    return _publish(path, data, create_only=create_only, private=private) is not None


def create_owned(
    path: Path,
    data: bytes,
    *,
    private: bool = False,
    security_source: Path | None = None,
    security_identity: tuple[int, int, int] | None = None,
    security_expected: bytes | None = None,
) -> tuple[bytes, tuple[int, int, int]]:
    """Create an owned stage, optionally preserving verified source permissions."""
    copying = security_source is not None
    if copying != (security_identity is not None) or copying != (security_expected is not None):
        raise ValueError("Security source requires its expected file identity and bytes")
    if copying and private:
        raise ValueError("Choose source permissions or private creation, not both")
    with ExitStack() as stack:
        attributes = None
        if security_source is not None:
            source = _absolute(security_source)
            parent = stack.enter_context(guarded_path(source.parent))
            handle = stack.enter_context(opened(source, parent=parent))
            if (
                info(handle).identity != security_identity
                or _read_handle(handle) != security_expected
            ):
                raise ValueError(f"Security source changed before owned stage creation: {source}")
            # Keep the source handle and captured descriptor alive through creation.
            # Stage files must not inherit a broader parent DACL on replacement.
            attributes = stack.enter_context(copied_attributes(handle))
        identity = _publish(
            path, data, create_only=True, private=private, security_attributes=attributes
        )
    if identity is None:
        raise FileExistsError(f"Managed destination already exists: {path}")
    return data, identity


def move_owned(
    source: Path, destination: Path, *, expected: bytes, expected_identity: tuple[int, int, int]
) -> None:
    """Capture/publish an exact opened object without overwriting any destination."""
    source, destination = _absolute(source), _absolute(destination)
    with (
        guarded_path(source.parent) as source_parent,
        guarded_path(destination.parent) as destination_parent,
        opened(source, access=_READ | _DELETE | _CONTROL, parent=source_parent) as handle,
    ):
        if info(handle).identity != expected_identity or _read_handle(handle) != expected:
            raise ValueError(f"Managed file changed before owned move: {source}")
        _rename(handle, destination, parent=destination_parent)


def conditional_remove(
    path: Path, *, expected: bytes, expected_identity: tuple[int, int, int]
) -> bool:
    path = _absolute(path)
    with (
        guarded_path(path.parent) as parent,
        opened(path, access=_READ | _DELETE | _CONTROL, parent=parent) as handle,
    ):
        if info(handle).identity != expected_identity or _read_handle(handle) != expected:
            return False
        _remove(handle)
        return True


@contextmanager
def guarded_project_identity(root: Path):
    with guarded_path(root) as handle:
        yield ":".join(str(part) for part in info(handle).identity)


def project_identity(root: Path) -> str:
    with guarded_project_identity(root) as identity:
        return identity


@contextmanager
def project_lock(key: str):
    account = local_app_data()
    with guarded_path(account) as account_handle:
        validate_private(account_handle, account_directory=True)
        namespace = account / "ai-dlc" / "locks"
        with (
            guarded_path(namespace, create_parents=True, private=True) as parent,
            private_attributes() as attributes,
            opened(
                namespace / f"{key}.lock",
                access=_READ | _WRITE | _CONTROL,
                share=3,
                creation=4,
                attributes=attributes,
                parent=parent,
            ) as handle,
        ):
            validate_private(handle)
            if info(handle).links != 1 or info(handle).attributes & _DIRECTORY:
                raise ValueError(
                    "Windows lock namespace requires a private regular single-link file"
                )
            overlapped = Overlapped()
            checked(api().lock(handle, 2, 0, 1, 0, c.byref(overlapped)))
            try:
                yield
            finally:
                checked(api().unlock(handle, 0, 1, 0, c.byref(overlapped)))
