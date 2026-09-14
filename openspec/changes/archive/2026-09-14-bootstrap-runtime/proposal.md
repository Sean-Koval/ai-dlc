# Find the bootstrap runtime and repair the shell entry

## Why
`ai-dlc project check --required` exits 1 with `runtime-unavailable: mise is not on PATH` in every shell that has not sourced the bootstrap PATH entry, although the bootstrap installed the runtime at the bootstrap bin directory. `ai-dlc project workspace-check` already detects the missing shell section but only describes it, and its repair action sends the user back to the bootstrap and `ai-dlc setup apply` rather than naming the one line the shell needs. Every worktree and every fresh terminal therefore repeats the same manual PATH edit before any check can run.

## What Changes
- Project check SHALL resolve the runtime manager from the bootstrap bin directory when PATH lacks it, note the substitution once on stderr with the permanent remedy, and refuse only when neither location has it. The check receipt is unchanged by the substitution, and the existing refusal to install tools during checks is kept.
- Workspace diagnostics SHALL name the exact activation line for the detected shell (bash, zsh or fish) in the activation result and in the finding for a missing owned shell section, and SHALL recognise fish activation in the same way as bash and zsh.
- `ai-dlc project workspace-init --shell` SHALL preview, and with `--apply` write, only the AI-DLC-owned section of the detected shell's rc file, preserving every authored line and the other owned lines, and SHALL refuse a symlinked, unreadable or non-regular rc file, an unsupported shell, and an owned section with authored edits.
- The bootstrap bin resolver moves to `ai_dlc.environment.bootstrap` so setup no longer reaches into documentation internals; the environment override it honours today is unchanged.

## Capabilities
### Modified Capabilities
- connected-project-readiness: RD-04 resolves the bootstrap runtime before refusing.
- project-workspace-diagnostics: WD-01 names the exact activation line; new WD-04 owned shell activation repair.

## Impact
`ai_dlc.setup.project.runtime_env`, `ai_dlc.documentation.workspace_diagnostics`, a new `ai_dlc.environment.bootstrap` module, the `project workspace-init` command, the machine enrollment runbook, the documentation guide, the tool maps and their tests. Which tools mise manages and the bootstrap installer are out of scope.
