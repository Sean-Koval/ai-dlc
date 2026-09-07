## Why

AI-DLC scaffolds preferred tools but currently hard-codes Linear in new projects
and guided connection. [Draft requirements](../../../docs/design/provider-toolsets-prd.md)
call for low-effort supported-provider selection and consistent harness setup.
Status: proposed; no implementation or remote configuration is approved by this artifact.

## What Changes

- Add explicit provider choices to scaffolding/adoption without changing legacy defaults.
- Reuse component/module/profile and native MCP rendering for reviewed toolset definitions.
- Separate common connection planning/apply from provider-specific discovery.
- Cover local Obsidian notes and optional desktop viewing accurately in readiness.
- Keep native connector readiness distinct from AI-DLC lifecycle adapter support.
- Generate selective Confluence/Obsidian guidance, reusing existing tools without site or vault mirroring.

## Capabilities

### New Capabilities
- `provider-toolset-onboarding`: select and prepare supported integrations consistently.

### Modified Capabilities
None. Existing behavior is preserved when new options are omitted.

## Impact

Copier questions/templates, templates and CLI services, provider onboarding,
component/readiness/provision services, native client rendering, bundled guidance
and module metadata. No new marketplace, daemon, credential store, or service hosting.
See the [implementation plan](../../../docs/superpowers/plans/2026-09-06-provider-toolset-onboarding.md).
