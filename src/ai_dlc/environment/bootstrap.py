"""Shared bootstrap location and explicit, owned shell activation."""

from __future__ import annotations

import os
import shlex
import stat
from collections.abc import Mapping
from pathlib import Path

from ai_dlc.errors import RefusedError
from ai_dlc.harness.agents import managed_section, read_managed_section


def bootstrap_bin(environ: Mapping[str, str], home: Path) -> Path:
    data = environ.get("XDG_DATA_HOME") or str(home / ".local/share")
    return Path(environ.get("AI_DLC_BOOTSTRAP_HOME") or f"{data}/ai-dlc/bootstrap") / "bin"


def shell_rc(shell: str, home: Path) -> Path:
    names = {"zsh": ".zshrc", "bash": ".bashrc", "fish": ".config/fish/config.fish"}
    if shell not in names:
        raise RefusedError(f"Unsupported shell: {shell or 'unknown'}")
    return home / names[shell]


def activation_line(shell: str, bin_dir: Path, home: Path) -> str:
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
            current, info = "", None
        else:
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or not info.st_mode & 0o444:
                    raise RefusedError("Shell rc file is not a readable regular file")
                with os.fdopen(fd, "r", closefd=False, newline="") as stream:
                    current = stream.read()
            finally:
                os.close(fd)
        found = read_managed_section(current, toml=True)
        if found["state"] not in {"absent", "present"}:
            raise RefusedError("Owned shell section is modified or malformed; resolve it first")
        lines = found.get("body", "").splitlines(keepends=True)
        kept = [item for item in lines if not item.startswith(("export PATH=", "set -gx PATH "))]
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
            with os.fdopen(fd, "w", closefd=False, newline="") as stream:
                stream.write(updated)
                stream.flush()
                os.ftruncate(fd, stream.tell())
                os.fsync(fd)
        finally:
            os.close(fd)
        return action, True
    finally:
        os.close(parent)


def _repair_rc_windows(rc: Path, line: str, apply: bool) -> tuple[str, bool]:
    import uuid

    from ai_dlc._windows_storage import (
        conditional_remove,
        create_owned,
        guarded_path,
        move_owned,
        safe_snapshot,
    )

    try:
        with guarded_path(rc.parent, create_parents=apply):
            try:
                original, identity = safe_snapshot(rc)
            except FileNotFoundError:
                original, identity = b"", None
            current = original.decode("utf-8")
            found = read_managed_section(current, toml=True)
            if found["state"] not in {"absent", "present"}:
                raise RefusedError("Owned shell section is modified or malformed; resolve it first")
            kept = [
                item
                for item in found.get("body", "").splitlines(keepends=True)
                if not item.startswith(("export PATH=", "set -gx PATH "))
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
                create_owned(rc, updated.encode("utf-8"), private=True)
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
    *, environ: Mapping[str, str] | None = None, home: Path | None = None, apply: bool = False
) -> dict:
    environment = dict(os.environ if environ is None else environ)
    home = home or Path(environment.get("HOME") or Path.home())
    shell = Path(environment.get("SHELL", "")).name
    rc = shell_rc(shell, home)
    bin_dir = bootstrap_bin(environment, home)
    if not bin_dir.is_dir():
        raise RefusedError("Bootstrap bin directory is absent; run the bootstrap first")
    line = activation_line(shell, bin_dir, home)
    try:
        action, applied = _repair_rc(rc, line, apply)
    except (OSError, UnicodeError) as exc:
        raise RefusedError(f"Shell rc file unavailable or unsafe: {rc}") from exc
    return {"shell": shell, "rc_file": str(rc), "line": line, "action": action, "applied": applied}
