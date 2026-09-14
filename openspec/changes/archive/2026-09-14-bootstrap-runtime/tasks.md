# Find the bootstrap runtime and repair the shell entry

## Implementation
- [x] 1.1 Move the bootstrap bin resolver and owned PATH-line parser to `ai_dlc.environment.bootstrap`, add the per-shell activation line, and make diagnostics and provisioning import them.
- [x] 1.2 Resolve `mise` from the bootstrap bin in `runtime_env` when PATH lacks it, note the substitution once, and keep the refusal when neither location has it, with tests for all three cases and an unchanged receipt digest.
- [x] 1.3 Name the exact activation line in the workspace-check activation result and in the activation-missing finding, and recognise fish activation, with tests.
- [x] 1.4 Add `project workspace-init --shell` preview and `--apply` writing of the owned section only, refusing symlinked or unreadable rc files and modified sections, with tests on temporary rc files.
- [x] 2.1 Update the machine enrollment runbook, documentation guide, tool maps and architecture map.

## Verification and delivery
- [x] 9.1 Record documentation-impact dispositions for the change.
- [x] 9.2 Validate this OpenSpec change and run required project checks.
Integration owner: refresh target-bound checks immediately before merging and finish both work records from the verified merge revision.
