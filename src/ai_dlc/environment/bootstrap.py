"""Shared bootstrap location and explicit, owned shell activation."""

from __future__ import annotations

import base64
import os
import platform
import re
import shlex
import stat
import subprocess
from collections.abc import Mapping
from pathlib import Path

from ai_dlc.errors import RefusedError
from ai_dlc.harness.agents import managed_section, read_managed_section


def _native_local_app_data() -> Path:
    """Ask Windows for the current user's actual local application-data directory."""
    import ctypes
    from ctypes import wintypes

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)  # pyright: ignore[reportAttributeAccessIssue]
    get_folder = shell32.SHGetFolderPathW
    get_folder.argtypes = [
        wintypes.HWND,
        ctypes.c_int,
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
    ]
    get_folder.restype = ctypes.c_long
    buffer = ctypes.create_unicode_buffer(32768)
    if get_folder(None, 28, None, 0, buffer) != 0 or not buffer.value:
        raise RefusedError(
            "Windows LocalAppData is unavailable; select AI_DLC_BOOTSTRAP_HOME explicitly"
        )
    return Path(buffer.value)


def bootstrap_bin(environ: Mapping[str, str], home: Path) -> Path:
    override = environ.get("AI_DLC_BOOTSTRAP_HOME")
    if override:
        return Path(override) / "bin"
    if platform.system() == "Windows":
        return _native_local_app_data() / "ai-dlc/bootstrap/bin"
    data = environ.get("XDG_DATA_HOME") or str(home / ".local/share")
    return Path(data) / "ai-dlc/bootstrap/bin"


def shell_rc(shell: str, home: Path) -> Path:
    names = {"zsh": ".zshrc", "bash": ".bashrc", "fish": ".config/fish/config.fish"}
    if shell not in names:
        raise RefusedError(f"Unsupported shell: {shell or 'unknown'}")
    return home / names[shell]


def activation_line(shell: str, bin_dir: Path, home: Path) -> str:
    if shell == "powershell":
        # ASCII source is safe in both inbox PowerShell's legacy encoding and UTF-8 profiles.
        encoded = base64.b64encode(str(bin_dir).encode("utf-8")).decode("ascii")
        return (
            "$aiDlcBootstrapBin = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"
            + encoded
            + "'))\n"
            "$env:PATH = (@($aiDlcBootstrapBin) + @($env:PATH -split ';' | "
            "Where-Object { $_ -and $_.TrimEnd('\\') -ine $aiDlcBootstrapBin.TrimEnd('\\') })) -join ';'\n"
            "if (Test-Path -LiteralPath (Join-Path $aiDlcBootstrapBin 'mise.exe')) { "
            "& (Join-Path $aiDlcBootstrapBin 'mise.exe') activate pwsh | Out-String | Invoke-Expression }"
        )
    shell_rc(shell, home)
    if bin_dir.is_relative_to(home):
        suffix = str(bin_dir.relative_to(home))
        suffix = (
            suffix.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
        )
        directory = f'"$HOME/{suffix}"'
    else:
        directory = shlex.quote(str(bin_dir))
    if shell == "fish":
        return f"set -gx PATH {directory} $PATH"
    if directory.startswith('"$HOME/'):
        return f'export PATH={directory[:-1]}:$PATH"'
    return f'export PATH={directory}:"$PATH"'


def configured_bin(body: str, home: Path) -> str | None:
    for line in body.splitlines():
        if line.startswith("$aiDlcBootstrapBin = "):
            matched = re.fullmatch(
                r"\$aiDlcBootstrapBin = \[Text.Encoding\]::UTF8.GetString\(\[Convert\]::FromBase64String\('([A-Za-z0-9+/=]+)'\)\)",
                line,
            )
            if not matched:
                return None
            try:
                value = base64.b64decode(matched[1], validate=True).decode("utf-8")
            except (ValueError, UnicodeError):
                return None
            return value if Path(value).is_absolute() else None
        try:
            if line.startswith("export PATH="):
                words = shlex.split(line.removeprefix("export PATH="))
                value = words[0][:-6] if len(words) == 1 and words[0].endswith(":$PATH") else None
            elif line.startswith("set -gx PATH "):
                words = shlex.split(line)
                value = words[3] if len(words) == 5 and words[4] == "$PATH" else None
            else:
                continue
        except ValueError:
            return None
        if value and value.startswith("$HOME/"):
            value = str(home / value[6:])
        return value if value and Path(value).is_absolute() else None
    return None


def _open_parent(path: Path, create: bool) -> int:
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
        return fd
    except BaseException:
        os.close(fd)
        raise


def _powershell_policy(environment: Mapping[str, str]) -> str:
    """Read inbox PowerShell's effective policy without running profiles or changing policy."""
    import ctypes
    from ctypes import wintypes

    if os.name != "nt":
        return "unknown"
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # pyright: ignore[reportAttributeAccessIssue]
    get_directory = kernel.GetSystemDirectoryW
    get_directory.argtypes = [wintypes.LPWSTR, wintypes.UINT]
    get_directory.restype = wintypes.UINT
    buffer = ctypes.create_unicode_buffer(32768)
    length = get_directory(buffer, len(buffer))
    if not length or length >= len(buffer):
        return "unknown"
    executable = Path(buffer.value) / "WindowsPowerShell/v1.0/powershell.exe"
    try:
        probe = subprocess.run(
            [
                str(executable),
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-ExecutionPolicy",
            ],
            env=dict(environment),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    value = probe.stdout.strip()
    return (
        value
        if probe.returncode == 0
        and value in {"Restricted", "AllSigned", "RemoteSigned", "Unrestricted", "Bypass"}
        else "unknown"
    )


def _profile_text(original: bytes) -> tuple[str, str]:
    encoding = (
        "utf-16-le"
        if original.startswith(b"\xff\xfe")
        else "utf-16-be"
        if original.startswith(b"\xfe\xff")
        else "utf-8"
    )
    return original.decode(encoding), encoding


def _repair_rc(rc: Path, line: str, apply: bool) -> tuple[str, bool]:
    if os.name == "nt":
        return _repair_rc_windows(rc, line, apply)
    try:
        parent = _open_parent(rc.parent, apply)
    except FileNotFoundError:
        return "create", False
    try:
        try:
            fd = os.open(rc.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except FileNotFoundError:
            current, info, encoding = "", None, "utf-8"
        else:
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or not info.st_mode & 0o444:
                    raise RefusedError("Shell rc file is not a readable regular file")
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    current, encoding = _profile_text(stream.read())
            finally:
                os.close(fd)
        if "# SIG # Begin signature block" in current:
            raise RefusedError(
                "Signed profile cannot be edited without invalidating its signature; use the direct executable"
            )
        found = read_managed_section(current, toml=True)
        if found["state"] not in {"absent", "present"}:
            raise RefusedError("Owned shell section is modified or malformed; resolve it first")
        lines = found.get("body", "").splitlines(keepends=True)
        kept = [
            item
            for item in lines
            if not item.startswith(
                (
                    "export PATH=",
                    "set -gx PATH ",
                    "$aiDlcBootstrapBin = ",
                    "$env:PATH = ",
                    "if (Test-Path -LiteralPath (Join-Path $aiDlcBootstrapBin ",
                )
            )
        ]
        body = line + "\n" + "".join(kept)
        if found["state"] == "absent":
            # Preserve every authored byte, including trailing whitespace.
            updated = (
                current
                + ("\n" if current and not current.endswith("\n") else "")
                + managed_section("", body, toml=True)
            )
        else:
            updated = managed_section(current, body, toml=True)
        action = (
            "unchanged"
            if updated == current
            else "create"
            if found["state"] == "absent"
            else "update"
        )
        if not apply or action == "unchanged":
            return action, False
        flags = os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        flags |= os.O_CREAT | os.O_EXCL if info is None else 0
        fd = os.open(rc.name, flags, 0o600, dir_fd=parent)
        try:
            actual = os.fstat(fd)
            if info is not None and (
                actual.st_dev,
                actual.st_ino,
                actual.st_mtime_ns,
                actual.st_size,
            ) != (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size):
                raise RefusedError("Shell rc changed during repair; retry after review")
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(updated.encode(encoding))
                stream.flush()
                os.ftruncate(fd, stream.tell())
                os.fsync(fd)
        finally:
            os.close(fd)
        return action, True
    finally:
        os.close(parent)


def _refuse_marked_profile(handle: int) -> None:
    """Inspect the held file's streams without following another pathname."""
    import ctypes
    import struct
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # pyright: ignore[reportAttributeAccessIssue]
    inspect = kernel.GetFileInformationByHandleEx
    inspect.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    inspect.restype = wintypes.BOOL
    size = 4096
    while size <= 1024 * 1024:
        buffer = ctypes.create_string_buffer(size)
        if inspect(handle, 7, buffer, size):  # FileStreamInfo
            break
        error = ctypes.get_last_error()  # pyright: ignore[reportAttributeAccessIssue]
        if error not in {122, 234}:  # insufficient buffer / more data
            raise RefusedError(
                f"Cannot safely inspect PowerShell profile streams (Windows {error})"
            )
        size *= 2
    else:
        raise RefusedError("PowerShell profile stream metadata exceeds inspection budget")
    offset = 0
    while True:
        if offset + 24 > size:
            raise RefusedError("PowerShell profile stream metadata is malformed")
        next_offset, length = struct.unpack_from("<II", buffer.raw, offset)
        if length % 2 or offset + 24 + length > size:
            raise RefusedError("PowerShell profile stream metadata is malformed")
        name = buffer.raw[offset + 24 : offset + 24 + length].decode("utf-16-le")
        if name.casefold() == ":zone.identifier:$data":
            raise RefusedError(
                "PowerShell profile carries Zone.Identifier; preserve its download marker and use the direct executable or a policy-approved manual profile review"
            )
        if not next_offset:
            return
        if next_offset < 24 + length or next_offset % 8:
            raise RefusedError("PowerShell profile stream metadata is malformed")
        offset += next_offset


def _repair_rc_windows(rc: Path, line: str, apply: bool) -> tuple[str, bool]:
    import uuid

    from ai_dlc._windows_storage import (
        conditional_remove,
        create_owned,
        guarded_path,
        move_owned,
        opened,
        safe_snapshot,
    )

    try:
        with guarded_path(rc.parent, create_parents=apply) as parent:
            try:
                with opened(rc, parent=parent) as handle:
                    _refuse_marked_profile(handle)
                    original, identity = safe_snapshot(rc)
            except FileNotFoundError:
                original, identity = b"", None
            current, encoding = _profile_text(original)
            if "# SIG # Begin signature block" in current:
                raise RefusedError(
                    "Signed profile cannot be edited without invalidating its signature; use the direct executable"
                )
            found = read_managed_section(current, toml=True)
            if found["state"] not in {"absent", "present"}:
                raise RefusedError("Owned shell section is modified or malformed; resolve it first")
            kept = [
                item
                for item in found.get("body", "").splitlines(keepends=True)
                if not item.startswith(
                    (
                        "export PATH=",
                        "set -gx PATH ",
                        "$aiDlcBootstrapBin = ",
                        "$env:PATH = ",
                        "if (Test-Path -LiteralPath (Join-Path $aiDlcBootstrapBin ",
                    )
                )
            ]
            body = line + "\n" + "".join(kept)
            updated = (
                current
                + ("\n" if current and not current.endswith("\n") else "")
                + managed_section("", body, toml=True)
                if found["state"] == "absent"
                else managed_section(current, body, toml=True)
            )
            action = (
                "unchanged"
                if updated == current
                else "create"
                if found["state"] == "absent"
                else "update"
            )
            if not apply or action == "unchanged":
                return action, False
            backup = rc.with_name(f".ai-dlc-profile-{uuid.uuid4().hex}")
            if identity is not None:
                move_owned(rc, backup, expected=original, expected_identity=identity)
            try:
                create_owned(rc, updated.encode(encoding), private=True)
            except BaseException as error:
                if identity is not None:
                    try:
                        move_owned(backup, rc, expected=original, expected_identity=identity)
                    except (OSError, ValueError):
                        error.add_note(
                            f"Original profile retained at {backup}; inspect before recovery"
                        )
                raise
            if identity is not None:
                conditional_remove(backup, expected=original, expected_identity=identity)
            return action, True
    except FileNotFoundError:
        if not apply:
            return "create", False
        raise


def plan_shell_activation(
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    apply: bool = False,
    powershell_profile: Path | None = None,
) -> dict:
    environment = dict(os.environ if environ is None else environ)
    home = home or Path(environment.get("HOME") or Path.home())
    if powershell_profile is not None:
        if not powershell_profile.is_absolute():
            raise RefusedError("PowerShell profile must be the absolute selected $PROFILE path")
        shell, rc = "powershell", powershell_profile
    elif platform.system() == "Windows":
        raise RefusedError(
            "Select the actual PowerShell profile with --powershell-profile $PROFILE; use the direct ai-dlc.exe path until activation"
        )
    else:
        shell = Path(environment.get("SHELL", "")).name
        rc = shell_rc(shell, home)
    bin_dir = bootstrap_bin(environment, home)
    if not bin_dir.is_dir():
        raise RefusedError("Bootstrap bin directory is absent; run the bootstrap first")
    policy = (
        _powershell_policy(environment)
        if shell == "powershell" and platform.system() == "Windows"
        else "not-assessed"
    )
    if apply and policy in {"Restricted", "AllSigned", "unknown"}:
        raise RefusedError(
            f"PowerShell profile policy {policy} prevents verified unsigned activation; use {bin_dir / 'ai-dlc.exe'} directly or an administrator-approved route. Policy is unchanged."
        )
    line = activation_line(shell, bin_dir, home)
    try:
        action, applied = _repair_rc(rc, line, apply)
    except (OSError, UnicodeError) as exc:
        raise RefusedError(f"Shell rc file unavailable or unsafe: {rc}") from exc
    result = {
        "shell": shell,
        "rc_file": str(rc),
        "line": line,
        "action": action,
        "applied": applied,
    }
    if shell == "powershell":
        result.update(
            {
                "direct_executable": str(bin_dir / "ai-dlc.exe"),
                "policy": policy,
                "profile_execution": "not-assessed",
                "next": "Open a fresh permitted PowerShell terminal and verify resolution; if policy blocks the profile, use the direct executable or your administrator-approved route.",
            }
        )
    return result
