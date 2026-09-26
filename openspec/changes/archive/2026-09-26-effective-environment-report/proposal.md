## Why

Two installations can report `0.4.0` while one runs the published release and another contains later source changes. Existing machine status reports enrollment/cache/credential drift but ignores its root; doctor and workspace diagnostics add useful scoped observations without a shareable parity contract. The [product direction](../../../docs/product-direction.md) promises reproducible selected tools and guidance with independent local bindings, not identical private client state.

## What Changes

- Extend existing `machine status` with explicit opt-in project-scoped redacted export and offline comparison modes; keep default status and doctor behavior compatible.
- Reuse existing diagnostics to report engine provenance, pinned profile/team sources, intended versus observed runtime/client state, project configuration/guidance and scoped authentication evidence.
- Define a bounded schema, deterministic identity and precise drift classes with unknown and expected differences visible.
- Surface the same safe report in explicit doctor mode without silently introducing provider probes.

## Capabilities

### New Capabilities
- `effective-environment-report`: EER-01 through EER-05.

### Modified Capabilities
None. Existing status/readiness/workspace-diagnostic contracts remain unchanged in their default modes. This additive export does not redefine authentication or release qualification.

## Impact

Application ownership remains `environment/` and existing setup/harness services; adapters own provider/client observations, and CLI/MCP remain thin. Canonical authorities: [machine enrollment](../../../docs/runbooks/machine-enrollment.md), [architecture](../../../docs/architecture.md), [tool map](../../../docs/workflows/tool-map.md), [work-computer setup](../../../docs/workflows/work-computer-setup.md), and [release verification](../../../docs/release-verification.md). Update their existing explanations and content-bound dispositions at implementation time; do not create a dashboard or second configuration store.

## Authorization and review status

The user authorized specifications and detailed issues for the reviewed team-adoption gaps. Priority P1. The CLI/schema, drift algorithm and digest rules are recommended technical design, not authorization to implement or proof of native parity. Owner: Sean Koval for product decisions; implementation owner unassigned. Status: proposed pending product/engineering review.

## Dependencies and exclusions

No native Windows setup dependency: unsupported observations remain explicit and the feature is independently deliverable on supported systems. Supplies stable identity for subsequent native harness evidence. Excludes account copying, secrets, private paths, native global configuration copying, chat history, remote synchronization, a new diagnostics service, automatic OAuth and paid runs. Actual cross-machine/native qualification remains #53.

## Planning review disposition — September 26, 2026

Reviewed against the current implementation, canonical requirements and the user's request to specify and publish the team-adoption recommendations. Scope, compatibility, dependencies and acceptance scenarios are accepted for this planning backlog. Commands and behaviors described as new remain proposed until implemented; no live platform/client qualification, release publication or paid evaluation is claimed. Implementation owner remains unassigned.
