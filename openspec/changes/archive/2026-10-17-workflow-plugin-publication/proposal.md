# Codex form of the workflow plugin and publication into a team harness

## Why

The workflow plugin should be one optional component of a team harness so
flightdeck can compare runs with and without it
([ADR 0001](../../../docs/decisions/0001-refocus-ai-dlc.md), job 1). The team runs
Codex as well as Claude Code (`agent-client = ["claude-code", "codex"]`), so the
component needs a Codex form, and the harness repository needs a safe, repeatable
way to receive it with digests it can pin. Tracks
[#193](https://github.com/Sean-Koval/ai-dlc/issues/193).

## What Changes

- `scripts/build_workflow_plugin.py` also writes `plugins/ai-dlc-workflow/native/codex/`:
  the same skill bytes, a Codex `hooks.json` running the shim, the shim,
  `AGENTS.fragment.md` and a `.codex-plugin/plugin.json` manifest (the spike showed
  Codex 0.162.1 loads skills and, once trusted, hooks from a local plugin).
- `plugin.lock.json` adds `files` (digest of every published Claude file) and
  `native.codex` (`content_digest` and `files`); the revision increases when either
  content digest changes.
- Add `scripts/publish_workflow_plugin.py --harness-repo PATH --dry-run|--apply`.
- Document the spike, the A/B arms, `autoUpdate: false`, hook trust and hangar's
  harden-mode limit in the plugin README.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `workflow-plugin`: WP-02 gains per-file and Codex digests; WP-06 adds the Codex
  form and WP-07 publication into a harness directory.

## Impact

Audience: maintainers of a team harness repository and flightdeck experiment
owners. Affected documents: `plugins/ai-dlc-workflow/README.md`, `README.md`
(workflow plugin section) and `docs/architecture.md`. Running the A/B (flightdeck),
hangar seed-dir mounting and the harness lock format (hangar) are out of scope.
The harness repository receives the component by pull request
(Sean-Koval/agent-factory `examples/team-harness/` until its own repository exists).
