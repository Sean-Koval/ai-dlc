## 1. Codex form

- [x] 1.1 Run the Codex 0.162.1 spike and record the evidence in the plugin README.
- [x] 1.2 Emit `native/codex/` (skills, hooks.json, shim, AGENTS fragment, `.codex-plugin` manifest) and extend `plugin.lock.json`.
- [x] 1.3 Test byte-identical skills, the hooks and manifest shape, recorded digests and the revision rule.

## 2. Publication

- [x] 2.1 Add `scripts/publish_workflow_plugin.py` with dry-run, apply, no-op re-apply and refusal of edited, unknown or foreign targets.
- [x] 2.2 Test against an empty directory, a repeat, hand edits, unknown files, a foreign directory, a legacy publication and a stale build.
- [x] 2.3 Open the harness repository pull request with the component pinned and the source commit recorded ([agent-factory#9](https://github.com/Sean-Koval/agent-factory/pull/9)).

## 3. Documentation and delivery

- [x] 3.1 Update the plugin README, README and architecture; record content-bound dispositions.
- [x] 3.2 Run the required checks.

## Subsequent delivery gates

Archive this change on its delivery branch with `ai-dlc work archive`, update from
the target branch and rerun required checks immediately before merge, and finish
through `ai-dlc work finish` against the merged revision.
