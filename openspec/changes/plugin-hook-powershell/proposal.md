# Guard PowerShell calls and fail closed in the workflow plugin hook

## Why

The plugin's PreToolUse hook denies destructive shell commands, but its matcher
names only `Bash`, `exec_command`, `Edit` and `Write`. Claude Code on native
Windows runs shell commands as the `PowerShell` tool, so there the hook never runs
and `rm` or `git reset --hard` goes through. The shim also allows a pre-tool call
whose payload it cannot read, and it leaves the destructive check to the CLI when
it delegates, so a broken or older CLI turns the check off. Tracks
[KAN-487](https://seanmkoval.atlassian.net/browse/KAN-487).

## What Changes

- The Claude plugin's PreToolUse matcher becomes `Bash|PowerShell|exec_command|Edit|Write`;
  the Codex matcher stays `Bash|exec_command`.
- `ai-dlc hook pre-tool` judges a `PowerShell` command like a `Bash` one, and denies
  a shell call that carries no command string.
- The shim applies its destructive check before delegating, so an older or broken
  CLI cannot allow a destructive command. A `PowerShell` line is judged
  case-insensitively, with backtick escapes and continuations resolved.
- The shim fails closed on pre-tool: an unreadable, empty or non-object payload, a
  shell call without a command string, or an error inside the shim exits 2.
  SessionStart and Stop still never block on a failure.
- The root lookup and delegate timeouts drop to 3 and 4 seconds, inside the
  client's 10 second hook timeout.

## Capabilities

### Modified Capabilities

- `workflow-plugin`: WP-05 adds `PowerShell` to the matcher and makes PreToolUse fail closed.

## Impact

A destructive command sent through Claude Code's PowerShell tool is now denied. On
native Windows without a working `python3`, the hook cannot start, which Claude
Code treats as a non-blocking error, so PowerShell calls run unguarded. The hooks
do not set `onFailure: "block"`, which would stop every call there. Native Windows
plugin hooks remain unsupported.
