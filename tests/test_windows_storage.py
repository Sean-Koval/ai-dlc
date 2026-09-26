"""Native storage contracts; skipped native cases are not Windows qualification."""

import os
import subprocess
import sys

import pytest

from ai_dlc.files import atomic_create, atomic_write

NATIVE = pytest.mark.skipif(os.name != "nt", reason="requires actual Windows NTFS/Win32 APIs")


@pytest.mark.parametrize(
    "relative",
    [
        r"C:escape",
        r"C:\escape",
        r"\\server\share\file",
        r"\\?\C:\file",
        "file:stream",
        "CON",
        "aux.txt",
        "trailing. ",
        r"..\escape",
    ],
)
def test_managed_relative_paths_reject_windows_escape_and_device_aliases(tmp_path, relative):
    with pytest.raises(ValueError):
        from ai_dlc._windows_storage import validate_relative

        validate_relative(relative)


def test_core_lock_import_does_not_require_unix_modules():
    script = """
import importlib.abc
import sys
class NoUnix(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {"pwd", "fcntl"}:
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0, NoUnix())
import ai_dlc.locking
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


@NATIVE
def test_native_publish_preserves_existing_destination_and_unicode(tmp_path):
    target = tmp_path / "sp ace é" / "managed.txt"
    atomic_write(target, "old\n")
    assert not atomic_create(target, "foreign\n", 0o600)
    assert target.read_text() == "old\n"
    atomic_write(target, "new\n")
    assert target.read_text() == "new\n"
    assert atomic_create(target.with_name("created.txt"), "private", 0o600)


@NATIVE
def test_native_guard_prevents_ancestor_replacement(tmp_path):
    from ai_dlc._windows_storage import guarded_path

    parent = tmp_path / "directory"
    parent.mkdir()
    with guarded_path(parent), pytest.raises(OSError):
        parent.rename(tmp_path / "moved")
    parent.rename(tmp_path / "moved")


@NATIVE
def test_native_sharing_failure_preserves_previous_bytes_and_retries(tmp_path):
    from ai_dlc._windows_storage import opened

    target = tmp_path / "managed.txt"
    atomic_write(target, "old")
    with opened(target):
        with pytest.raises(OSError):
            atomic_write(target, "new")
        assert target.read_text() == "old"
    atomic_write(target, "new")
    assert target.read_text() == "new"


@NATIVE
def test_native_junction_is_refused_without_touching_target(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    junction = tmp_path / "junction"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)], check=True, capture_output=True
    )
    with pytest.raises(ValueError, match="reparse"):
        atomic_write(junction / "escaped.txt", "unsafe")
    assert not (target / "escaped.txt").exists()


@NATIVE
def test_native_lock_case_aliases_and_killed_holder_recover(tmp_path):
    script = """
import sys
from pathlib import Path
from ai_dlc.locking import project_write_lock
with project_write_lock(Path(sys.argv[1])):
    print("held", flush=True)
    sys.stdin.read()
"""
    holder = subprocess.Popen(
        [sys.executable, "-c", script, str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    contender = None
    try:
        assert holder.stdout.readline().strip() == "held"
        contender = subprocess.Popen(
            [sys.executable, "-c", script, str(tmp_path).swapcase()],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        with pytest.raises(subprocess.TimeoutExpired):
            contender.communicate(timeout=0.3)
        holder.kill()
        holder.wait(timeout=10)
        out, _ = contender.communicate(timeout=10)
        assert out.strip() == "held"
    finally:
        for child in (holder, contender):
            if child is not None and child.poll() is None:
                child.kill()
                child.wait()


@NATIVE
def test_native_lock_nested_and_ignores_untrusted_home(tmp_path, monkeypatch):
    from ai_dlc.locking import project_write_lock

    monkeypatch.setenv("HOME", str(tmp_path / "not-an-account"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "untrusted-local-app-data"))
    with project_write_lock(tmp_path), project_write_lock(tmp_path):
        atomic_write(tmp_path / "nested.txt", "complete")
    assert (tmp_path / "nested.txt").read_text() == "complete"
    assert not (tmp_path / "untrusted-local-app-data").exists()


@NATIVE
def test_native_owned_move_refuses_same_bytes_replacement_and_existing_destination(tmp_path):
    from ai_dlc._windows_storage import create_owned, move_owned

    source, destination = tmp_path / "stage", tmp_path / "destination"
    data, identity = create_owned(source, b"owned")
    source.rename(tmp_path / "original")
    source.write_bytes(data)
    with pytest.raises(ValueError, match="changed"):
        move_owned(source, destination, expected=data, expected_identity=identity)
    assert source.read_bytes() == data
    assert not destination.exists()
    original = tmp_path / "original"
    destination.write_bytes(b"authored")
    with pytest.raises(OSError):
        move_owned(original, destination, expected=data, expected_identity=identity)
    assert original.read_bytes() == b"owned"
    assert destination.read_bytes() == b"authored"


@NATIVE
def test_native_created_stage_cannot_be_replaced_while_publishing(tmp_path, monkeypatch):
    from ai_dlc import _windows_storage as storage

    real_write = storage._write_handle
    refused = []

    def attempt_swap(handle, data):
        stage = next(tmp_path.glob(".ai-dlc-*"))
        with pytest.raises(OSError):
            stage.rename(tmp_path / "stolen")
        refused.append(True)
        real_write(handle, data)

    monkeypatch.setattr(storage, "_write_handle", attempt_swap)
    storage.atomic_publish(tmp_path / "file", b"complete")
    assert refused and (tmp_path / "file").read_bytes() == b"complete"
    assert not (tmp_path / "stolen").exists()


@NATIVE
def test_native_bounded_read_and_private_dacl_refuse_broad_access(tmp_path):
    from ai_dlc._windows_storage import create_owned, safe_read

    target = tmp_path / "private"
    create_owned(target, b"secret", private=True)
    assert safe_read(target, max_bytes=6, private=True) == b"secret"
    with pytest.raises(ValueError, match="exceeds"):
        safe_read(target, max_bytes=5)
    subprocess.run(
        ["icacls", str(target), "/grant", "*S-1-1-0:(R)"], capture_output=True, check=True
    )
    with pytest.raises(ValueError, match="DACL"):
        safe_read(target, private=True)
    assert target.read_bytes() == b"secret"


@NATIVE
def test_native_remove_operates_on_verified_identity(tmp_path):
    from ai_dlc._windows_storage import conditional_remove, create_owned

    target = tmp_path / "managed"
    data, identity = create_owned(target, b"same")
    target.rename(tmp_path / "old")
    target.write_bytes(data)
    assert not conditional_remove(target, expected=data, expected_identity=identity)
    assert target.read_bytes() == data
    assert conditional_remove(tmp_path / "old", expected=data, expected_identity=identity)
    assert not (tmp_path / "old").exists()


@NATIVE
def test_native_lock_refuses_shared_namespace_file(tmp_path):
    import hashlib

    from ai_dlc._windows_storage import project_identity, project_lock
    from ai_dlc._windows_storage._security import local_app_data

    key = hashlib.sha256(project_identity(tmp_path).encode()).hexdigest()
    with project_lock(key):
        pass
    leaf = local_app_data() / "ai-dlc" / "locks" / f"{key}.lock"
    subprocess.run(["icacls", str(leaf), "/grant", "*S-1-1-0:(R)"], capture_output=True, check=True)
    try:
        with pytest.raises(ValueError, match="DACL"), project_lock(key):
            pass
    finally:
        subprocess.run(
            ["icacls", str(leaf), "/remove:g", "*S-1-1-0"], capture_output=True, check=True
        )


@NATIVE
def test_native_shell_repair_preserves_authored_bytes_and_refuses_modified_section(tmp_path):
    from ai_dlc.environment.bootstrap import _repair_rc
    from ai_dlc.errors import RefusedError

    rc = tmp_path / "profile.ps1"
    rc.write_bytes(b"# authored\r\n")
    assert _repair_rc(rc, "native activation placeholder", True)[1]
    assert rc.read_bytes().startswith(b"# authored\r\n")
    modified = rc.read_bytes().replace(b"native activation placeholder", b"authored managed edit")
    rc.write_bytes(modified)
    with pytest.raises(RefusedError, match="modified"):
        _repair_rc(rc, "native activation placeholder", True)
    assert rc.read_bytes() == modified


@NATIVE
def test_native_project_lock_holds_root_identity_until_exit(tmp_path):
    from ai_dlc.locking import project_write_lock

    project = tmp_path / "project"
    project.mkdir()
    with project_write_lock(project), pytest.raises(OSError):
        project.rename(tmp_path / "replacement")
    project.rename(tmp_path / "replacement")


@NATIVE
def test_native_parent_attribute_reparse_attack_cannot_redirect_creation(tmp_path, monkeypatch):
    """An attributes-only open bypasses sharing rules; traversal must use handles."""
    import ctypes as c
    import struct
    from ctypes import wintypes as w

    from ai_dlc import _windows_storage as storage

    parent, outside = tmp_path / "parent", tmp_path / "outside"
    parent.mkdir()
    outside.mkdir()
    substitute = ("\\??\\" + str(outside)).encode("utf-16-le")
    display = str(outside).encode("utf-16-le")
    path_bytes = substitute + b"\0\0" + display + b"\0\0"
    data = (
        struct.pack(
            "<IHHHHHH",
            0xA0000003,
            8 + len(path_bytes),
            0,
            0,
            len(substitute),
            len(substitute) + 2,
            len(display),
        )
        + path_bytes
    )
    device_io = c.WinDLL("kernel32", use_last_error=True).DeviceIoControl
    device_io.argtypes = [
        w.HANDLE,
        w.DWORD,
        c.c_void_p,
        w.DWORD,
        c.c_void_p,
        w.DWORD,
        c.POINTER(w.DWORD),
        c.c_void_p,
    ]
    device_io.restype = w.BOOL
    original = storage.open_relative
    attacked = []
    attack_errors = []

    def attack_then_open(handle, name, access, share, creation, attributes, directory):
        if name.startswith(".ai-dlc-") and not attacked:
            with storage.opened(parent, access=0x100, share=7) as attacker:
                count = w.DWORD()
                applied = bool(
                    device_io(attacker, 0x000900A4, data, len(data), None, 0, c.byref(count), None)
                )
                attacked.append(applied)
                attack_errors.append(c.get_last_error())
        result = original(handle, name, access, share, creation, attributes, directory)
        if attacked and attacked[0] and list(outside.iterdir()):
            storage.api().close(result)
            pytest.fail("Handle-relative open created a stage through the attacker junction")
        return result

    monkeypatch.setattr(storage, "open_relative", attack_then_open)
    try:
        try:
            storage.atomic_publish(parent / "file", b"must stay in original directory")
        except (OSError, ValueError):
            pass  # Safe refusal is permitted if a raced parent becomes a reparse point.
        assert attacked == [True], (
            f"Native attribute-only attack was not exercised: {attack_errors}"
        )
        assert not (outside / "file").exists()
        assert not list(outside.iterdir()), "No staging bytes may escape through the junction"
    finally:
        if attacked and attacked[0]:
            # RemoveDirectory removes the junction, not the target directory.
            parent.rmdir()


@NATIVE
def test_native_inside_supports_existing_directory_and_rejects_junction(tmp_path):
    from ai_dlc.files import inside

    target = tmp_path / "docs"
    target.mkdir()
    assert inside(tmp_path, "docs") == target
    junction = tmp_path / "linked"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)], check=True, capture_output=True
    )
    with pytest.raises((OSError, ValueError)):
        inside(tmp_path, "linked")


@NATIVE
def test_native_owned_stage_preserves_source_acl_and_refuses_replaced_identity(tmp_path):
    import ctypes as c
    from ctypes import wintypes as w

    from ai_dlc._windows_storage import create_owned, opened
    from ai_dlc._windows_storage._api import api, checked
    from ai_dlc._windows_storage._security import copied_attributes

    def descriptor(path):
        convert = c.WinDLL(
            "advapi32", use_last_error=True
        ).ConvertSecurityDescriptorToStringSecurityDescriptorW
        convert.argtypes = [c.c_void_p, w.DWORD, w.DWORD, c.POINTER(w.LPWSTR), c.c_void_p]
        convert.restype = w.BOOL
        from ai_dlc._windows_storage._api import SecurityAttributes

        with opened(path) as handle, copied_attributes(handle) as attributes:
            descriptor = c.cast(attributes, c.POINTER(SecurityAttributes)).contents.descriptor
            text = w.LPWSTR()
            checked(convert(descriptor, 1, 0x1 | 0x4, c.byref(text), None))
            try:
                return text.value
            finally:
                api().free(c.cast(text, c.c_void_p))

    source = tmp_path / "restricted"
    before, identity = create_owned(source, b"before", private=True)
    acl = descriptor(source)
    stage = tmp_path / "replacement"
    create_owned(
        stage,
        b"after",
        security_source=source,
        security_identity=identity,
        security_expected=before,
    )
    assert descriptor(stage) == acl
    assert stage.read_bytes() == b"after"
    source.rename(tmp_path / "original")
    source.write_bytes(before)
    with pytest.raises(ValueError, match="changed"):
        create_owned(
            tmp_path / "refused",
            b"after",
            security_source=source,
            security_identity=identity,
            security_expected=before,
        )
    assert not (tmp_path / "refused").exists()


@NATIVE
def test_native_create_only_preserves_broad_existing_permissions_without_claiming_private(tmp_path):
    from ai_dlc._windows_storage import atomic_publish, create_owned, safe_read

    target = tmp_path / "authored"
    create_owned(target, b"authored", private=True)
    subprocess.run(
        ["icacls", str(target), "/grant", "*S-1-1-0:(R)"], capture_output=True, check=True
    )
    assert not atomic_publish(target, b"secret", private=True, create_only=True)
    assert target.read_bytes() == b"authored"
    with pytest.raises(ValueError, match="DACL"):
        safe_read(target, private=True)
    with pytest.raises(ValueError, match="DACL"):
        atomic_publish(target, b"secret", private=True)
    assert target.read_bytes() == b"authored"
