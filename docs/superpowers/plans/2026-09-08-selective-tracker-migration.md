# Remaining Selective Tracker Migration Implementation Plan

> Execute sequentially with test-driven development; independent review is coordinator-owned.

**Goal:** Complete local evidence, substitution and reviewed target-reconciliation gaps without repeating PR23 migration.
**Architecture:** Version existing migration evidence while preserving schema1; isolate optional creation reconciliation from the local transaction and reuse Registry/contracts/Journal.
**Tech Stack:** Python, TOML work records, immutable JSON plans/receipts, SQLite mutation journal, pytest transport fixtures.
**Spec:** [TM01–06](../../../openspec/changes/selective-tracker-migration/specs/selective-tracker-migration/spec.md).

## Constraints
No implicit source reads, live calls, remote rollback, Jira migration, terminal-state inference or new finish policy. Retain Plane ownership and durable-intent safeguards. Independent review and live qualification remain separate.

## Task 1: Evidence and actual adapter substitution
- [x] Write failing source-unknown/omission, target state/capability and schema1 compatibility cases in tests/test_tracker_migration.py.
- [x] Implement schema2 evidence in src/ai_dlc/tracker_migration.py, preserving exact schema1 revalidation/recovery.
- [x] Add real Registry GitHub/Plane transport matrix with owned targets, account/project drift, unowned refusal, gate preservation and interrupted local transaction.
- [x] Run affected checks and record actual red/green evidence.

## Task 2: Explicit target creation
- [x] Add red cases for saved reviewed intent, partial batch, accepted-but-lost response, local drift, retained targets, exact fingerprint conflict and competing sender election.
- [x] Implement separate src/ai_dlc/tracker_targets.py using existing contracts/Journal and migration plan builders; never save bindings.
- [x] Add distinct CLI creation-preview/reconciliation actions and tests, refusing combined intent/actions.
- [x] Verify retry is read-only after uncertainty/staleness; return retained target mapping and ordinary local plan only after all targets and local snapshot are current.
- [x] Update docs/migration.md, current parent status and scoped work record/evidence.
- [ ] Run coordinator-owned integrated required checks after independent review. Focused/static and strict validation precede the frozen candidate; do not archive or finish parent live gates.
