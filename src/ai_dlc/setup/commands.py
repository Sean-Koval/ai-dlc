"""The project's small explicit command union, without shell inference."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_dlc.errors import RefusedError


class CommandUnavailable(RefusedError):
    """A command's selected executable or shell cannot be launched safely."""


@dataclass(frozen=True)
class Command:
    argv: tuple[str, ...]
    shell: str | None = None


def parse_command(value: Any) -> Command:
    """Validate the whole declaration before resolving any executable or runtime."""
    if isinstance(value, str):
        return _script("posix", value)
    if not isinstance(value, dict):
        raise RefusedError("expected a POSIX string, argv record or explicit shell/script record")
    if set(value) == {"argv"}:
        argv = value["argv"]
        if (
            not isinstance(argv, list)
            or not argv
            or any(not isinstance(item, str) or "\0" in item for item in argv)
            or not argv[0].strip()
        ):
            raise RefusedError("argv requires a nonblank executable and NUL-free string arguments")
        return Command(tuple(argv))
    if set(value) == {"shell", "script"} and value["shell"] in ("posix", "powershell"):
        return _script(value["shell"], value["script"])
    raise RefusedError("expected exactly argv or shell (posix|powershell) and script")


def _script(shell: str, script: Any) -> Command:
    if not isinstance(script, str) or not script.strip() or "\0" in script:
        raise RefusedError("script must be a nonblank NUL-free string")
    if shell == "posix":
        return Command(("sh", "-c", script), shell)
    return Command(
        ("powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script),
        shell,
    )


def find_executable(name: str, root: Path, env: dict[str, str]) -> str | None:
    """Resolve against the child working directory and PATH, including native suffixes."""
    path = Path(name)
    if path.is_absolute() or path.parent != Path(".") or name.startswith(("./", ".\\")):
        candidate = path if path.is_absolute() else root / path
        return shutil.which(str(candidate), path=env.get("PATH", ""))
    search = os.pathsep.join(
        str(Path(entry) if Path(entry).is_absolute() else root / entry)
        for entry in env.get("PATH", os.defpath).split(os.pathsep)
    )
    if os.name != "nt":
        return shutil.which(name, path=search)
    # Passing absolute candidates avoids Windows' implicit process-current-directory lookup.
    for directory in search.split(os.pathsep):
        found = shutil.which(str(Path(directory) / name), path=search)
        if found:
            return found
    return None


def require_executable(command: Command, root: Path, env: dict[str, str]) -> str:
    executable = find_executable(command.argv[0], root, env)
    if executable is None:
        if command.shell == "posix":
            raise CommandUnavailable(
                "POSIX shell sh is unavailable; install the project's selected POSIX shell "
                "or migrate this command to an explicit argv/powershell record"
            )
        if command.shell == "powershell":
            raise CommandUnavailable(
                "selected Windows PowerShell powershell.exe is unavailable; provide the "
                "selected shell or choose a supported explicit command record"
            )
        raise CommandUnavailable(
            f"executable {command.argv[0]!r} is unavailable on the controlled PATH; "
            "run the project's explicit setup or install its declared prerequisite"
        )
    if os.name == "nt" and Path(executable).suffix.lower() in {".cmd", ".bat"}:
        raise CommandUnavailable(
            f"batch executable {command.argv[0]!r} requires an explicit shell record; "
            "native argv never invokes .cmd/.bat through an implicit shell"
        )
    return executable
