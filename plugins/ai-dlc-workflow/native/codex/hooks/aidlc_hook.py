"""AI-DLC workflow plugin hook shim: degrade cleanly without the ai-dlc CLI.

This file is the single source of ``plugins/ai-dlc-workflow/hooks/aidlc_hook.py``;
``scripts/build_workflow_plugin.py`` copies it byte for byte. It must stay
standard-library only (Python 3.10+) and must not import ``ai_dlc``.

Usage: ``python3 aidlc_hook.py {session-start|pre-tool|stop}`` with the client's
JSON hook payload on stdin.

The shim delegates to ``ai-dlc hook <event>`` only when ``ai-dlc`` is on PATH,
``ai-dlc.toml`` exists at the repository root and the session is not inside a
hangar sandbox (``HANGAR_WORKSPACE`` or ``HANGAR_JOB_ID`` set). Otherwise it
denies only destructive shell commands, never applies the bound-push policy,
and writes nothing to disk. ``AI_DLC_HOOKS=off`` disables every event and
``AI_DLC_HOOKS=quiet`` suppresses the session-start line. Only exit 2 blocks;
every other outcome exits 0 so a hook can never wedge a session.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import IO, Any

EVENTS = ("session-start", "pre-tool", "stop")
HANGAR_VARIABLES = ("HANGAR_WORKSPACE", "HANGAR_JOB_ID")
DELEGATE_TIMEOUT_SECONDS = 8
DESTRUCTIVE_REASON = (
    "Destructive operation denied by the ai-dlc workflow plugin: this hook cannot request "
    "native approval. Review and authorize it through the client's native controls, or set "
    "AI_DLC_HOOKS=off to disable the plugin hooks."
)
NOT_ADOPTED_LINE = (
    "ai-dlc workflow plugin active; this repo is not adopted, so lifecycle commands are "
    "unavailable."
)
NO_CLI_LINE = (
    "ai-dlc workflow plugin active; ai-dlc is not on PATH, so lifecycle commands are unavailable."
)
HANGAR_LINE = (
    "ai-dlc workflow plugin active; inside a hangar sandbox, so lifecycle commands are "
    "unavailable and hangar owns verification and landing."
)


def classify_command(command: str) -> str:
    """Classify one shell command; shared by ``ai_dlc.harness.hooks`` and the plugin."""
    try:
        words = shlex.split(command)
    except ValueError:
        return "unsupported"
    if any(x in command for x in [";", "&&", "||", "|", "\n", "$(", "`"]):
        return "unsupported"
    if words[:1] == ["rm"]:
        return "destructive"
    if words[:2] == ["git", "reset"] and "--hard" in words[2:]:
        return "destructive"
    if words[:2] == ["git", "clean"] and any(
        flag == "--force" or (flag.startswith("-") and not flag.startswith("--") and "f" in flag)
        for flag in words[2:]
    ):
        return "destructive"
    if words[:2] == ["git", "push"] and any(
        flag in {"-f", "--force", "--delete", "-d", "--mirror"}
        or flag.startswith(("--force-with-lease", ":"))
        for flag in words[2:]
    ):
        return "destructive"
    if words[:2] == ["git", "push"] or words[:3] == ["gh", "pr", "create"]:
        return "bound-operation"
    if words[:1] == ["git"] and "push" in words:
        return "unsupported"
    return "ordinary"


def in_hangar(env: Mapping[str, str]) -> bool:
    return any(env.get(name) for name in HANGAR_VARIABLES)


def repository_root(payload: Mapping[str, Any], env: Mapping[str, str]) -> Path:
    """The repository top level for the session, falling back to its working directory."""
    cwd = payload.get("cwd")
    start = Path(cwd if isinstance(cwd, str) and cwd else env.get("CLAUDE_PROJECT_DIR") or ".")
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return start
    top = result.stdout.strip()
    return Path(top) if result.returncode == 0 and top else start


def delegate_mode(
    root: Path, env: Mapping[str, str], which: Callable[[str], str | None]
) -> tuple[str | None, str]:
    """Return (ai-dlc executable or None, the static line used when not delegating)."""
    if in_hangar(env):
        return None, HANGAR_LINE
    executable = which("ai-dlc")
    if not executable:
        return None, NO_CLI_LINE
    if not (root / "ai-dlc.toml").is_file():
        return None, NOT_ADOPTED_LINE
    return executable, ""


def _delegate(
    executable: str,
    event: str,
    root: Path,
    payload: Mapping[str, Any],
    stdout: IO[str],
    stderr: IO[str],
) -> int:
    try:
        result = subprocess.run(
            [executable, "hook", event, "--root", str(root)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=DELEGATE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        stderr.write(f"ai-dlc workflow plugin: ai-dlc hook {event} did not run ({exc}); allowed.\n")
        return 0
    if result.returncode == 2:
        stderr.write(result.stderr)
        return 2
    if result.returncode != 0:
        stderr.write(
            f"ai-dlc workflow plugin: ai-dlc hook {event} exited {result.returncode}; allowed.\n"
        )
        return 0
    stdout.write(result.stdout)
    return 0


def run(
    argv: list[str],
    stdin: IO[str],
    stdout: IO[str],
    stderr: IO[str],
    env: Mapping[str, str],
    which: Callable[[str], str | None] = shutil.which,
) -> int:
    """Handle one hook event and return the process exit code (only 2 blocks)."""
    mode = env.get("AI_DLC_HOOKS", "").strip().lower()
    if mode == "off":
        return 0
    event = argv[1] if len(argv) > 1 else ""
    if event not in EVENTS:
        stderr.write(f"ai-dlc workflow plugin: unknown hook event {event!r}; allowed.\n")
        return 0
    try:
        payload = json.loads(stdin.read() or "{}")
    except (ValueError, UnicodeDecodeError):
        payload = None
    if not isinstance(payload, dict):
        # A malformed payload carries no command to judge; never block on it.
        if event == "pre-tool":
            return 0
        payload = {}
    root = repository_root(payload, env)
    executable, line = delegate_mode(root, env, which)
    if executable:
        return _delegate(executable, event, root, payload, stdout, stderr)
    if event == "session-start":
        if mode != "quiet":
            stdout.write(line + "\n")
        return 0
    if event == "stop":
        return 0
    tool_input = payload.get("tool_input")
    data = tool_input if isinstance(tool_input, dict) else {}
    command = data.get("command", data.get("cmd", ""))
    if isinstance(command, str) and classify_command(command) == "destructive":
        stderr.write(DESTRUCTIVE_REASON + "\n")
        return 2
    # The bound-push policy belongs to adopted local repositories; hangar's verify
    # gate and landing own publication inside sandboxes.
    return 0


def main() -> int:
    try:
        return run(sys.argv, sys.stdin, sys.stdout, sys.stderr, os.environ)
    except Exception as exc:  # noqa: BLE001 -- a hook must never wedge a session
        sys.stderr.write(f"ai-dlc workflow plugin: hook failed ({exc}); allowed.\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
