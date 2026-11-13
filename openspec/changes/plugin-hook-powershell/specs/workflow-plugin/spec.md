## MODIFIED Requirements

### Requirement: WP-05 CLI-optional hooks

The plugin hooks SHALL run `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/aidlc_hook.py
<event>` in exec form with a 10 second timeout, PreToolUse matching
`Bash|PowerShell|exec_command|Edit|Write` in the Claude plugin and
`Bash|exec_command` in the Codex form. The shim SHALL use only the standard
library. It SHALL judge `Bash`, `PowerShell` and `exec_command` calls alike. It
SHALL delegate to `ai-dlc hook <event>` only when `ai-dlc` is on PATH,
`ai-dlc.toml` exists at the repository root and neither `HANGAR_WORKSPACE` nor
`HANGAR_JOB_ID` is set. Otherwise SessionStart SHALL print one static line (none
when `AI_DLC_HOOKS=quiet`), PreToolUse SHALL deny destructive commands with exit 2
using the same classifier as `ai_dlc.harness.hooks` and allow everything else
without applying the bound-push policy, and Stop SHALL do nothing.
`AI_DLC_HOOKS=off` SHALL exit 0 for every event. For a shell call, PreToolUse
SHALL apply the shim's destructive check before delegating, so the CLI's version
or failure cannot allow a destructive command, and SHALL judge a `PowerShell` line
case-insensitively with its backtick escapes and continuations resolved. A
delegate exit other than 0 or 2, or a delegate timeout, SHALL then allow.
PreToolUse SHALL fail closed: an unreadable, empty or non-object payload, a call
that names no tool and carries no command string, a shell call without a command
string, or an error inside the shim SHALL exit 2. A call from any other named tool
SHALL be allowed. For
SessionStart and Stop, a malformed payload, a delegate failure or an error SHALL
allow with exit 0. The shim SHALL NOT execute or persist the command and SHALL NOT
create `.ai-dlc/` in a repository.

#### Scenario: Hangar job in an adopted repository
- **WHEN** `HANGAR_WORKSPACE` or `HANGAR_JOB_ID` is set in an adopted repository with `ai-dlc` installed and no work record, and the payload is `git push origin feature/x`
- **THEN** the hook allows it without delegating

#### Scenario: Destructive command without the CLI
- **WHEN** `rm -rf build` arrives in any mode except `AI_DLC_HOOKS=off`
- **THEN** the hook exits 2 with a reason

#### Scenario: Destructive PowerShell command
- **WHEN** a `PowerShell` call runs `git reset --hard` or ``git reset `--hard``, with or without the CLI
- **THEN** the hook exits 2 with a reason

#### Scenario: Unreadable pre-tool payload
- **WHEN** a PreToolUse payload is not a JSON object, or a shell call has no command string
- **THEN** the hook exits 2, while the same payload for SessionStart or Stop exits 0

#### Scenario: Adopted local repository
- **WHEN** the repository is adopted, `ai-dlc` is on PATH and no hangar variable is set
- **THEN** the hook denies a destructive command itself, delegates anything else, passes through the CLI's exit 2 denial and maps any other delegate failure to allow
