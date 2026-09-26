# Finish from an owned merged checkout

## Why

[Product direction](../../../docs/product-direction.md) prioritizes useful evidence services with measured, modest process cost. Existing finish gates correctly demand the bound PR's exact merged revision, but after the target branch advances the caller must manually create, enter and remove a detached checkout. This is mechanical coordination work and introduces avoidable path, configuration and cleanup errors.

## What Changes

- Add explicit `ai-dlc work finish WORK_ID --at-merge` as a bounded helper that resolves the bound merged PR and uses an owned isolated detached checkout to invoke existing finish gates.
- Preserve the caller's branch, files, local bindings, credentials and operation-journal identity; reject conflicting work/provider identity rather than retargeting.
- Handle missing objects, blocked gates, interrupted/uncertain completion, retries and failed cleanup visibly without duplicate tracker writes or deleting user content.
- Keep plain finish behavior and manual recovery available; update its remedy and canonical/generated guidance to explain the helper.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `spec-delivery-traceability`: modify TR-04's recovery guidance and add FMC-01 through FMC-05 for the explicit helper.

## Impact

Audience: delivery maintainers and agents finishing already merged work. Implementation belongs in existing work application services behind a thin CLI option; use SCM, specification and journal contracts. Review `docs/development-workflow.md`, `docs/workflows/tool-map.md`, `docs/verification/delivery-path-baseline.md`, generated lifecycle guidance and catalog mappings. Record content-bound documentation dispositions for affected targets.

No automatic merge, rebase, conflict resolution, push, archive, CI repair, waiting daemon or bypass of trusted receipts. No remote completion is authorized merely by creating this specification. Implementation and live qualification remain future delivery work.

## Planning review disposition — September 26, 2026

Reviewed against the current implementation, canonical requirements and the user's request to specify and publish the team-adoption recommendations. Scope, compatibility, dependencies and acceptance scenarios are accepted for this planning backlog. Commands and behaviors described as new remain proposed until implemented; no live platform/client qualification, release publication or paid evaluation is claimed. Implementation owner remains unassigned.
