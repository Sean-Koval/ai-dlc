# Keep source bootstrap from repointing the global ai-dlc aliases

## Why
Source bootstrap builds a separate environment per checkout but always repointed the shared `ai-dlc` and `ai-dlc-cli` aliases at the checkout it was run from. `AGENTS.md` tells every checkout to run that command, including linked worktrees created for agent sessions, so any session that followed the instructions silently changed the `ai-dlc` every other shell used. On 2026-09-11 an agent session bootstrapped its worktree and the global `ai-dlc` switched to that worktree's older code, which lacked `--version` and the new project commands, until the main checkout was bootstrapped again.

## What Changes
- Source bootstrap SHALL leave an existing working shared alias unchanged, and SHALL publish it on explicit request or when no working alias exists. Release mode SHALL keep publishing the aliases.
- A source environment SHALL record the checkout it was synced from, and bootstrap output SHALL say which checkout the shared alias runs.
- Workspace diagnostics SHALL attribute the selected shared alias to a checkout and report when it is not this one.

## Capabilities
### Added Capabilities
- bootstrap-executable-publication: Shared alias publication is explicit rather than a side effect of preparing a checkout.

### Modified Capabilities
- project-workspace-diagnostics: The shared alias is attributed to the checkout it runs.

## Impact
The bootstrap script and its scaffold copy, the workspace diagnostics service, their tests, and machine enrollment guidance. No installed executable bytes, download verification, staging retention or release-mode behavior changes, and no alias is removed.
