# Proportionate push policy

## Why

[Product direction](../../../docs/product-direction.md) says teams should add tracked delivery when needed and use small artifacts for small work. Current development guidance permits a change without a tracker or formal specification, but the optional bound-push hook denies all direct pushes and PR creation without a reviewed tracker-bound record. Teams selecting the hook cannot express the documented lightweight path without disabling it or inventing a record.

## What Changes

- Add explicit project-owned `agents.bound_push_policy` with `all-branches` as the unchanged default and `tracked-branches` as the lightweight opt-in.
- In tracked-branches mode allow only demonstrably unbound branches; preserve validation and denial for invalid bound records or unreadable work state that prevents determining association.
- Reject non-project attempts to set this policy, retain native hook capability boundaries and describe the selected policy accurately in guidance and diagnostics.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `native-work-harnesses`: add PPP-01 through PPP-04 for project-owned optional bound-push policy.

## Impact

Audience: maintainers choosing hook policy and agents publishing small changes. Implementation touches configuration validation, hook decisions, generated guidance, and their tests; no external provider operation is added. Review `docs/development-workflow.md`, `docs/workflows/tool-map.md`, relevant machine/client runbooks, packaged configuration examples and `docs/catalog.toml` mappings. Existing destructive-operation denials, payload limitations and finish gates remain unchanged.

No heuristic based on changed paths, branch name, commit size or inferred risk; no per-branch exemption record; no machine-local waiver; no automatic tracker creation; no broader hook-coverage claim. This specification delivery contains no implementation.

## Planning review disposition — September 26, 2026

Reviewed against the current implementation, canonical requirements and the user's request to specify and publish the team-adoption recommendations. Scope, compatibility, dependencies and acceptance scenarios are accepted for this planning backlog. Commands and behaviors described as new remain proposed until implemented; no live platform/client qualification, release publication or paid evaluation is claimed. Implementation owner remains unassigned.
