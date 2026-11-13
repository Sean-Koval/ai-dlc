"""ai-dlc workflow plugin hook shim: degrade cleanly without the ai-dlc CLI.

This file is the single source of ``plugins/ai-dlc-workflow/hooks/aidlc_hook.py``;
``scripts/build_workflow_plugin.py`` copies it byte for byte. It must stay
standard-library only (Python 3.10+) and must not import ``ai_dlc``.

Usage: ``python3 aidlc_hook.py {session-start|pre-tool|stop}`` with the client's
JSON hook payload on stdin. A pre-tool Edit or Write payload is delegated only when
it targets ``docs/specs``; every other edit is allowed at once. Shell calls arrive as
``Bash``, ``PowerShell`` (Claude Code on native Windows) or ``exec_command`` (Codex).

The shim delegates to ``ai-dlc hook <event>`` only when ``ai-dlc`` is on PATH,
``ai-dlc.toml`` exists at the repository root and the session is not inside a
hangar sandbox (``HANGAR_WORKSPACE`` or ``HANGAR_JOB_ID`` set). Otherwise it
denies only destructive shell commands, never applies the bound-push policy,
and writes nothing to disk. ``AI_DLC_HOOKS=off`` disables every event and
``AI_DLC_HOOKS=quiet`` suppresses the session-start line. Only exit 2 blocks.

A pre-tool call fails closed: a payload the shim cannot read, a shell call without a
command string, or an error inside the shim exits 2, and a delegate that gives no
verdict (any exit but 0 or 2, or a timeout) falls back to the shim's own destructive
check. session-start and stop never block on a failure, so they cannot wedge a session.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import IO, Any

EVENTS = ("session-start", "pre-tool", "stop")
# File-edit tools the PreToolUse matcher also routes here. Only an edit under
# docs/specs has guidance (ai-dlc hook warns to reconcile the reviewed work record);
# every other edit is allowed without starting the CLI.
EDIT_TOOLS = ("Edit", "Write")
# Shell tools whose command the hook judges: Claude Code's Bash and, on native Windows,
# PowerShell; Codex's exec_command (its command is under "cmd").
SHELL_TOOLS = ("Bash", "PowerShell", "exec_command")
SPECIFICATION_DIRECTORY = ("docs", "specs")
HANGAR_VARIABLES = ("HANGAR_WORKSPACE", "HANGAR_JOB_ID")
# Root lookup (3 s) plus the delegate (4 s) stays inside the client's 10 s hook timeout,
# so the shim answers before the client kills it.
ROOT_TIMEOUT_SECONDS = 3
DELEGATE_TIMEOUT_SECONDS = 4
DESTRUCTIVE_REASON = (
    "Destructive operation denied by the ai-dlc workflow plugin: this hook cannot request "
    "native approval. Review and authorize it through the client's native controls, or set "
    "AI_DLC_HOOKS=off to disable the plugin hooks."
)
UNJUDGED_REASON = (
    "Blocked by the ai-dlc workflow plugin: it could not read a command to check in this "
    "tool call. Set AI_DLC_HOOKS=off to disable the plugin hooks."
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


# Characters that end one simple command inside a shell line: lists (; & && ||), pipes,
# newlines, subshells and command substitution ($( ) and backticks).
SEPARATORS = ";&|()`\n"
# A PowerShell script block ({ ... } after ForEach-Object, try, if) holds commands too.
POWERSHELL_SEPARATORS = SEPARATORS + "{}"
# Windows runs a program named without these extensions too (PATHEXT).
PROGRAM_EXTENSIONS = (".exe", ".cmd", ".bat", ".com")
# When segments disagree, the strictest category wins.
SEVERITY = ("ordinary", "unsupported", "bound-operation", "destructive")
# PowerShell's own ways to delete: Remove-Item and its built-in aliases. A POSIX shell has
# only rm; in PowerShell rm is one more alias of Remove-Item. Like rm, any call is denied.
POWERSHELL_DELETES = frozenset({"remove-item", "ri", "rm", "del", "erase", "rd", "rmdir"})


def command_segments(command: str, separators: str = SEPARATORS) -> list[list[str]] | None:
    """Split a shell line into the words of each simple command, or None if unparseable."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=separators)
    lexer.whitespace = " \t\r"  # a newline separates commands, so it is punctuation here
    lexer.whitespace_split = True
    segments: list[list[str]] = [[]]
    try:
        for token in lexer:
            if token and all(character in separators for character in token):
                segments.append([])
            else:
                segments[-1].append(token)
    except ValueError:
        return None
    return [segment for segment in segments if segment]


def shell_text(tool: object, command: str) -> str:
    """The command text to classify for one shell tool.

    PowerShell is case-insensitive and uses the backtick as its escape and line
    continuation, where a POSIX shell uses it for substitution. So a PowerShell line is
    lowercased, its continuations joined and its escapes resolved before classifying:
    ``git reset `--hard`` is judged as ``git reset --hard``.
    """
    if tool != "PowerShell":
        return command
    text = re.sub(r"`\r?\n", " ", command.lower())
    text = re.sub("`[\"']", "", text)  # an escaped quote neither opens nor closes a string
    text = text.replace("` ", "\u00a0")  # an escaped space stays inside its word
    text = re.sub(r"`(.)", r"\1", text, flags=re.DOTALL)
    # A backslash is a path separator in PowerShell, never an escape, so the POSIX
    # tokenizer must not swallow it: C:\Git\cmd\git.exe is read as C:/Git/cmd/git.exe.
    return text.replace("\\", "/")


def classify_shell(tool: object, command: str) -> str:
    """Classify the command of one shell tool call, in that shell's own terms."""
    return classify_command(shell_text(tool, command), powershell=tool == "PowerShell")


def classify_command(command: str, *, powershell: bool = False) -> str:
    """Classify a shell line; shared by ``ai_dlc.harness.hooks`` and the plugin.

    A compound line (``a && b``, ``a; b``, a pipe, a newline or a substitution) is
    classified by its strictest simple command, so chaining cannot hide a destructive
    or bound operation. A program is known by its name alone, so ``/usr/bin/git`` and
    ``git.exe`` are ``git``. With ``powershell``, the line is one ``shell_text`` prepared,
    a script block's commands are judged too and PowerShell's own deletes count as ``rm``. Commands reached through wrappers such
    as ``sh -c``, ``env``, ``cmd /c`` or ``Invoke-Expression`` are not inspected.
    """
    segments = command_segments(command, POWERSHELL_SEPARATORS if powershell else SEPARATORS)
    if segments is None:
        return "unsupported"
    categories = [_classify_words(words, powershell) for words in segments] or ["ordinary"]
    return max(categories, key=SEVERITY.index)


def program_name(word: str) -> str:
    """A program as its name alone: no directory and, as Windows resolves it, no extension."""
    name = word.rsplit("/", 1)[-1]
    for extension in PROGRAM_EXTENSIONS:
        if name.lower().endswith(extension):
            return name[: -len(extension)]
    return name


def _classify_words(words: list[str], powershell: bool = False) -> str:
    """Classify the words of one simple command."""
    if powershell and words[0] == "." and len(words) > 1:
        words = words[1:]  # dot-sourcing runs the program like a call
    words = [program_name(words[0]), *words[1:]]
    if words[0] == "rm" or (powershell and words[0] in POWERSHELL_DELETES):
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
            timeout=ROOT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return start
    top = result.stdout.strip()
    return Path(top) if result.returncode == 0 and top else start


def specification_edit(payload: Mapping[str, Any], root: Path) -> bool:
    """Whether an Edit or Write payload targets a file under the repository's docs/specs."""
    tool_input = payload.get("tool_input")
    file_path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(file_path, str) or not file_path:
        return False
    try:
        relative = (root / file_path).resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return relative.parts[:2] == SPECIFICATION_DIRECTORY


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
) -> int | None:
    """Run ``ai-dlc hook``; return its exit code, or None when it gave no verdict."""
    fallback = "allowed after the plugin's own check" if event == "pre-tool" else "allowed"
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
        stderr.write(
            f"ai-dlc workflow plugin: ai-dlc hook {event} did not run ({exc}); {fallback}.\n"
        )
        return None
    if result.returncode == 2:
        stderr.write(result.stderr)
        return 2
    if result.returncode != 0:
        stderr.write(
            f"ai-dlc workflow plugin: ai-dlc hook {event} exited {result.returncode}; {fallback}.\n"
        )
        return None
    stdout.write(result.stdout)
    return 0


def local_pre_tool(payload: Mapping[str, Any], stderr: IO[str]) -> int:
    """The shim's own pre-tool verdict: deny destructive commands, fail closed otherwise."""
    tool = payload.get("tool_name")
    if isinstance(tool, str) and tool not in SHELL_TOOLS:
        return 0  # Edit, Write and any other named tool carry no shell command
    tool_input = payload.get("tool_input")
    data = tool_input if isinstance(tool_input, dict) else {}
    command = data.get("command", data.get("cmd"))
    if not isinstance(command, str):
        stderr.write(UNJUDGED_REASON + "\n")
        return 2
    if classify_shell(tool, command) == "destructive":
        stderr.write(DESTRUCTIVE_REASON + "\n")
        return 2
    # The bound-push policy belongs to adopted local repositories; hangar's verify
    # gate and landing own publication inside sandboxes.
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
        raw = stdin.read()
        # A client always sends a pre-tool payload, so an empty one is unreadable there.
        payload = json.loads(raw if raw.strip() or event == "pre-tool" else "{}")
    except (ValueError, UnicodeDecodeError):
        payload = None
    if not isinstance(payload, dict):
        # A malformed pre-tool payload may still be a shell call: fail closed. The other
        # events have nothing to judge, so they carry on with an empty payload.
        if event == "pre-tool":
            stderr.write(UNJUDGED_REASON + "\n")
            return 2
        payload = {}
    root = repository_root(payload, env)
    tool = payload.get("tool_name")
    if event == "pre-tool":
        if tool in EDIT_TOOLS and not specification_edit(payload, root):
            return 0
        # The shim's own check runs first, so neither a broken CLI nor one older than
        # this plugin (which may not know a shell tool such as PowerShell) can let a
        # destructive command through. The CLI then adds the bound-push policy.
        verdict = local_pre_tool(payload, stderr)
        if verdict or not (tool in SHELL_TOOLS or tool in EDIT_TOOLS):
            return verdict
    executable, line = delegate_mode(root, env, which)
    if executable:
        code = _delegate(executable, event, root, payload, stdout, stderr)
        return 0 if code is None else code
    if event == "session-start" and mode != "quiet":
        stdout.write(line + "\n")
    return 0


def main() -> int:
    try:
        return run(sys.argv, sys.stdin, sys.stdout, sys.stderr, os.environ)
    except Exception as exc:  # noqa: BLE001 -- only a pre-tool failure may block
        if (
            sys.argv[1:2] == ["pre-tool"]
            and os.environ.get("AI_DLC_HOOKS", "").strip().lower() != "off"
        ):
            sys.stderr.write(f"ai-dlc workflow plugin: hook failed ({exc}); blocked.\n")
            return 2
        sys.stderr.write(f"ai-dlc workflow plugin: hook failed ({exc}); allowed.\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
