## Why

AI-DLC now supports reviewed GitHub Issues/Projects selection and setup alongside
legacy Linear. The remaining work makes supported connections and native harness
setup reusable. [Draft requirements](../../../../docs/design/provider-toolsets-prd.md)
call for low-effort supported-provider selection and consistent harness setup.
Status: current remaining scope under GitHub #19, authorized by the maintainer
on September 7. Delivered GitHub selection/Project defaults are dependencies;
this artifact does not establish live work-system access.

## What Changes

- Add explicit provider choices to scaffolding/adoption without changing legacy defaults.
- Reuse component/module/profile and native MCP rendering for reviewed toolset definitions.
- Separate common connection planning/apply from provider-specific discovery.
- Cover local Obsidian notes and optional desktop viewing accurately in readiness.
- Keep native connector readiness distinct from AI-DLC lifecycle adapter support.
- Integrate explicit Claude/Antigravity project support through its bounded child.
- Defer custom Confluence/shared-knowledge integration to #22 until its server is available.

## Capabilities

### New Capabilities
- `provider-toolset-onboarding`: select and prepare supported integrations consistently.

### Modified Capabilities
None. Existing behavior is preserved when new options are omitted.

## Impact

Copier questions/templates, templates and CLI services, provider onboarding,
component/readiness/provision services, native client rendering, bundled guidance
and module metadata. No new marketplace, daemon, credential store, or service hosting.
See the [implementation plan](2026-09-06-provider-toolset-onboarding.md).
