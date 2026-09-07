## Why

The maintainer selected GitHub Issues and Projects as the first personal tracker,
with future Plane selection intended to be configuration/onboarding. This child
implements the GitHub slice of the authorized provider plans. Confluence is
deferred; Plane hosting is not required.

## What Changes

- Typed tracker capability discovery drives work start without vendor branching.
- Existing GitHub issue operations compose with optional Projects v2 status mapping.
- Explicit scaffold and guided connection choices preserve legacy defaults.
- Selected/default-only migration preserves old work, references and finish gates.

## Capabilities

### New Capabilities
- `github-ticket-workflows`: capability-based issue and optional board workflow.

### Modified Capabilities
None. Existing external providers without discovery retain legacy behavior.

## Impact

Python contracts/providers/workflow, scaffold/onboarding, migration services,
provider guidance, regression tests. No implicit remote migration, new board,
Plane installation, Confluence integration, archive or merge.
