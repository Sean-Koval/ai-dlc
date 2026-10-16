## 1. Hook shim (#192)

- [x] 1.1 Add the standard-library shim in `src/ai_dlc/harness/hook_shim.py` and make `ai_dlc.harness.hooks` import its classifier.
- [x] 1.2 Test every event in delegated, no-CLI, unadopted and both hangar modes; the kill switch, quiet mode, malformed payloads, delegate failure and timeout; isolated `python3 -I -S` execution; classifier parity; and the hangar push regression against the real CLI.

## 2. Plugin build (#191)

- [x] 2.1 Guard `ai-dlc` instructions in the included source skills, relock digests and re-render this repository's skill copies.
- [x] 2.2 Add `scripts/build_workflow_plugin.py` with `--check`, generate and commit `plugins/ai-dlc-workflow/`, and run its drift check from `scripts/check_generated.py`.
- [x] 2.3 Test determinism, digest refusal, stale detection, revision increase, lock contents, hook shape and guide filtering.
- [x] 2.4 Run `claude plugin validate --strict` and load the plugin with `--plugin-dir` in a scratch repository without `ai-dlc.toml` or `ai-dlc` on PATH.

## 3. Documentation and delivery

- [x] 3.1 Write the plugin README and update README, architecture, tool map, playbook, capabilities coverage and catalog; record content-bound dispositions.
- [x] 3.2 Run the required checks.

## Subsequent delivery gates

Archive this change on its delivery branch with `ai-dlc work archive`, update from
the target branch and rerun required checks immediately before merge, and finish
through `ai-dlc work finish` against the merged revision. Publishing the plugin to
the team harness repository is #193.
