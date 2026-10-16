# Package the workflow as one optional Claude Code plugin

## Why

[ADR 0001](../../../docs/decisions/0001-refocus-ai-dlc.md) keeps one workflow
plugin in scope. Today AI-DLC's guidance, hooks and skills reach an agent only by
rendering files into an adopted repository, so none of it reaches a hangar sandbox
and nobody can measure whether it helps. One opt-in plugin lets a team harness
carry the workflow as a single component that flightdeck can switch on and off.
The rendered hooks also shell out to `ai-dlc`; without the CLI they error on every
matched tool call, and with it the default `all-branches` push policy would deny
the pushes hangar jobs make. The plugin variant must degrade cleanly. Tracks
[#191](https://github.com/Sean-Koval/ai-dlc/issues/191) and
[#192](https://github.com/Sean-Koval/ai-dlc/issues/192).

## What Changes

- Add `scripts/build_workflow_plugin.py [--check]`, which generates the committed
  `plugins/ai-dlc-workflow/` directory: manifest, a provider-neutral guide skill,
  ten team skills, exec-form hooks, the hook shim and `plugin.lock.json` with
  per-component digests and a content digest. The `generated` required check runs
  the builder's drift check.
- Add `src/ai_dlc/harness/hook_shim.py`, a standard-library hook shim that
  delegates to `ai-dlc hook` only in adopted repositories with the CLI outside
  hangar, and otherwise denies only destructive commands. `ai_dlc.harness.hooks`
  reuses its classifier.
- Guard the `ai-dlc` instructions in the included skills with the adoption
  condition, editing the source skills once and relocking their digests.
- No new CLI command; `ai-dlc agents render` output for adopted repositories is
  unchanged.

## Capabilities

### New Capabilities

- `workflow-plugin`: WP-01 to WP-05 cover the build, the lock and digest, the
  guide content, opt-in loading and CLI-optional hooks.

### Modified Capabilities

None.

## Impact

Audience: maintainers publishing the plugin to the team harness repository
(#193) and agents running with it. Affected documents: `README.md`,
`docs/architecture.md`, `docs/workflows/tool-map.md`, `playbook/README.md`,
`agents/capabilities.toml` coverage, the new `plugins/ai-dlc-workflow/README.md`
and `docs/catalog.toml`. Codex packaging, marketplace publication, MCP servers in
the plugin and changes to bound-push defaults for adopted repositories are out of
scope. Loading the plugin in a hangar sandbox is hangar work.
