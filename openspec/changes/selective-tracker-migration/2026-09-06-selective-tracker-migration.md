> Historical record. Retained for provenance, not current implementation guidance.
> Consult docs/index.md, canonical OpenSpec requirements and the tracker.

# Selective Tracker Migration Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans after migration-mode review. Plan creation does not authorize target issue creation.

**Goal:** Switch future work or selected retained work without silently redirecting existing records.
**Architecture:** Extend existing rebind through an explicit migration service; reconcile remote targets before atomic local mapping and provenance receipts.
**Tech Stack:** Existing Python, work records, journals, project locking and provider adapters.
**Spec:** [selective-tracker-migration](specs/selective-tracker-migration/spec.md).

Historical plan: PR23 delivered default-only and verified existing-target mapping. Continue through the [September 8 plan](2026-09-08-selective-tracker-migration.md); unchecked historical tasks are not a current delivery inventory. The implemented descriptor-based local transaction is bounded and non-atomic, as documented in docs/migration.md. Status: superseded execution detail. [Master constraints](../../../docs/archive/planning/2026-09-06-provider-toolsets.md) apply. The current
read-only preview covers 13 baseline records; do not hard-code that count.
The personal destination is GitHub Issues and Projects. The authorized GitHub
child implements default-only and verified selected mappings first. Resumable
remote target creation remains a separate parent task; migrate active/planned
Linear work only after exact mapping/creation review.

## Task 1: Default-only selection preserves old work

**Files:** create `src/ai_dlc/tracker_migration.py`, `tests/test_tracker_migration.py`;
adapt `rebind.py`, `workflow.py`, `cli.py`; retain `tests/test_rebind.py` behavior.
**Interface:** `plan_tracker_migration(root: Path, provider_id: str, *, mode: str, work_ids: list[str], mappings: dict) -> dict` where mode is `default-only` or `selected`.
`apply_tracker_migration(root: Path, plan: dict, *, environ) -> dict` consumes that
exact plan. Preview never creates remote items or writes shared files.

- [ ] Add a red test with one explicitly bound record and one legacy unbound record:

```python
def test_default_switch_preserves_bound_and_legacy_work(migration_project):
    root, original_bound = migration_project
    plan = plan_tracker_migration(root, "plane-personal", mode="default-only",
                                  work_ids=[], mappings={})
    apply_tracker_migration(root, plan, environ={})
    assert (root / ".ai-dlc/work/bound.toml").read_bytes() == original_bound
    assert load_project(root)["roles"]["tracker"] == "plane-personal"
    assert WorkService.from_project(root).load("legacy")["providers"]["tracker"] == "linear"
```

- [ ] Build the fixture from real TOML with preserved old provider config and a local registered target definition; no remote login is required for default-only mutation.
- [ ] Verify red, implement old-effective-binding freeze and atomic local switch, and refuse stale source/work digests or unknown target definitions.
- [ ] Test unchanged unrelated references, old aliases, explicit existing drift, and new-record defaults. Run focused suites and commit.

## Task 2: Selected mappings, resumable target creation and receipts

**Files:** same migration service/tests, existing `journal.py` and provider interfaces;
add `tests/test_tracker_migration_recovery.py` and migration guidance in docs/.
**Interfaces:** consume existing tracker read/find/create; `reconcile_migration_targets(root: Path, plan: dict, *, environ) -> dict` requires explicit reviewed create intent and returns resolved mappings or uncertainty, never applies local bindings.

- [ ] Add red tests for selected versus unselected records, wrong-project target, missing mapping, post-preview work changes and verified mapping when source access is unavailable.
- [ ] Implement schema-1 local plan validation and fresh target identity checks. Only selected records change; durable receipts store old/new references and operation ID.
- [ ] Add accepted-but-timed-out target creation and local-publication-failure regressions. Retry must reuse known targets and retain old local bindings until the full selected mapping is valid.
- [ ] Implement target reconciliation using existing journals; never delete remote targets as compensation for a local failure.
- [ ] Test omitted remote-only history labeling and explicit local-record-only source. Reject unknown source completeness claims and preserve all finish gates.
- [ ] Run focused tests, required checks and strict spec validation; review and commit.

## Task 3: Real migration rehearsal before production selection

**Files:** add a versioned run report under `docs/verification/`, update user runbook.
**Consumes:** a qualified selected target adapter and explicit disposable
repository/project authorization. GitHub qualification does not depend on Plane.

- [ ] Parameterize migration/recovery tests across Linear to GitHub Issues, Linear
  to Plane, and GitHub Issues to Plane (and reverse); use the same service path.
  Report unsupported target states without losing original state/provenance.
- [ ] Rehearse default-only switching and a selected mapping with a simulated connection interruption, retaining source evidence.
- [ ] Inspect old/new references, account boundaries, source/target state, rollback and resume outcomes.
- [ ] Generate the real repository migration preview from current records and present the concrete mappings and omissions to the maintainer.
- [ ] Apply real migration only after that reviewed mapping is selected. Record evidence and complete the child through the configured lifecycle; a rebind is never a work finish.

Coverage: Task 1 TM-01/TM-05; Task 2 TM-02/TM-03/TM-04/TM-05; Task 3 TM-06 and observed qualification.
