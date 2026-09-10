## Why

Existing rebind requires mappings for all retained work and does not copy remote
issues. Users need to choose a new default independently from migration, especially
when the old service becomes unavailable. PR23 delivered the GitHub default-only and selected verified-target mapping slice. Remaining local work covers explicit source/state evidence, actual adapter substitution fixtures and optional reconciled creation; real Plane qualification remains pending.
[Requirements](../../../docs/design/provider-toolsets-prd.md).

## What Changes

- Add a default-only switch that freezes retained effective bindings before changing defaults.
- Add selected-record migration preview with explicit destination verification and provenance.
- Reconcile optional target creation before any local binding change.
- Retain old provider configuration and source references for unmigrated work.

## Capabilities

### New Capabilities
- `selective-tracker-migration`: deliberate default changes and selected-work migration.

### Modified Capabilities
None. Legacy all-record rebind remains available and keeps its mapping requirements.

## Impact

Rebind/work services, local migration plans/journals, CLI, instructions and tests.
No source deletion, complete ticket-history import, new completion evidence, or
implicit remote writes. [Plan](2026-09-06-selective-tracker-migration.md).
