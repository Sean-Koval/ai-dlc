# Render shared guidance for selected capabilities

## Why

`_shared_guidance_lines` currently gives every adopted project instructions for a
tracker, OpenSpec archives, pull-request merge preparation and merged-revision
finish, even when those roles are absent or a different specification provider is
selected. This makes partial adoption misleading and spends session context on
inapplicable workflow. The existing component index already reflects project
selection; the surrounding prose must reflect the same project boundary without
mistaking a component's installation metadata for executable provider support.

## What Changes

- Compose the managed shared guidance from the existing project roles and actual
  built-in runtime provider kinds, including supported aliases.
- Include generic specification and tracker instructions only for selected roles;
  reserve OpenSpec archive commands for the OpenSpec runtime provider.
- Include SCM merge advice only for supported selected SCM, work-finish advice
  only for the supported tracker-plus-SCM lifecycle, and OpenSpec checkout advice
  only when that lifecycle selects OpenSpec.
- Keep required checks, provider and bundle indexes, authored text, and managed
  update/conflict behavior intact. Local projects retain useful configuration,
  repository documentation and verification guidance.

## Capabilities

### Modified Capabilities

- `native-work-harnesses`: NH-06 defines conditional shared guidance and its
  compatibility boundaries.
- `spec-delivery-traceability`: TR-04 scopes generated OpenSpec merged-revision
  advice to the applicable delivery configuration; gate behavior is unchanged.

## Delivery Slice

Draft local work ID: `capability-scoped-guidance`. Owner: repository maintainers.
User authorization covers specification followed by implementation; the parent
task owns the work record, review and tracker publication. `requires_spec=true`
because generated instructions change observably. Requirements: NH-06 and TR-04.
No dependency on the other efficiency slices: this change is independently
reviewable and finishable against existing configuration and provider contracts.

Excluded: new providers, a workflow DSL, config schema changes, provider health
probes, runtime gate changes, local terminal completion, skill selection changes,
and rewriting project-authored workflow policy. Generated guidance is an
instruction surface, not evidence of live qualification.

## Impact

Implementation and tests: `src/ai_dlc/harness/agents.py`,
`tests/test_agents_phases.py`, `tests/test_rendering.py`, and generated guidance
for this repository. The canonical operator explanation is
`docs/runbooks/machine-enrollment.md`; the delivery-gate procedure remains in
`docs/workflows/design-to-implementation.md`. Review catalog-mapped documents,
including `docs/verification/documentation-workflow.md`, for content-bound impact
dispositions. Update existing authority; no new durable documentation home or
qualification claim is needed.
