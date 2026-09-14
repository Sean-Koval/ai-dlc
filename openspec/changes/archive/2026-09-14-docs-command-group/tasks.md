# Fold the documentation commands into `ai-dlc docs`

## Implementation
- [x] 1.1 Add the `ai-dlc docs` group with exactly `check`, `review`, `gate`, `read`, `search` and `init`, with CLI tests for the help listing, each mode flag and the usage errors.
- [x] 1.2 Keep every `project docs-*` command as a hidden alias that calls the same helper and prints one deprecation line to stderr, with tests that the existing invocations keep their stdout and exit status.
- [x] 1.3 Switch this repository's `documentation` check to `ai-dlc docs gate`, re-render `AGENTS.md`, and rename the commands in the shipped skills, README, documentation index, tool maps and their template twins, the template documentation guide, the runbook, the knowledge design and the verification narrative's navigation text.

## Verification and delivery
- [x] 9.1 Record documentation-impact dispositions for the change.
- [x] 9.2 Validate this OpenSpec change and run required project checks.
Integration owner: refresh target-bound checks, merge the reviewed PR and finish from verified merged-revision evidence.
