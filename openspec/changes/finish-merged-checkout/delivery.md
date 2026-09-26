# Delivery slice: finish-merged-checkout

Proposed local work ID: `finish-merged-checkout`. Priority: P2.
Owner: Sean Koval, product decision; implementation owner unassigned.
Status: specification and issue preparation authorized; implementation not started.
Review source: September 26 team-adoption review and the user's request to specify and create issues. No remote tracker completion, implementation or release is authorized by this document.
Canonical brief authority: [product direction](../../../docs/product-direction.md). Review trace: OUT-001 and RQ-005; formal acceptance resides in this change.

## Problem and outcome

After main advances past a PR's merge, correct finish behavior requires a manual detached checkout solely to read exact-merge specification evidence. Deliver an explicit helper that owns that checkout and delegates to existing finish gates, preserving the user's working files and identity. The desired saving is fewer mechanical commands; no numerical productivity gain is asserted before measurement.

## Scope and exclusions

Include `work finish WORK_ID --at-merge`, bound PR/SHA resolution, owned isolated detached checkout, merged-policy authority, caller local bindings and operation-state continuity, retry reconciliation and safe cleanup. Plain finish stays compatible. Exclude automatic fetch, merge/rebase, conflict repair, push, archiving, CI bypass, background waits, generic worktree management and automatic release publication.

## Specification decision

requires_spec: true.
spec_reason: Adds an explicit finish-helper operation, resource/recovery behavior and updated merged-revision remedy while retaining existing completion authority.
Formal source: [spec-delivery-traceability delta](specs/spec-delivery-traceability/spec.md).
Requirements: FMC-01, FMC-02, FMC-03, FMC-04, FMC-05 and modified TR-04. Existing exact merged-revision gates and portable-development completion requirements remain mandatory.

## Dependencies and interfaces

depends_on: [] — independently finishable using existing work, SCM, specification and journal services. Source interfaces: `src/ai_dlc/work/workflow.py` (`WorkService.from_project`, `finish`), `src/ai_dlc/work/journal.py`, `src/ai_dlc/providers/scm.py`, specification adapters, locking/filesystem helpers and the work-finish CLI handler. Existing behavior was inspected at 3d4ffc1; fresh remote dependency status is not asserted.

Native-Windows work owns portability implementation/qualification of core filesystem primitives. This helper must use the existing platform abstraction available when implemented and must report unqualified targets honestly; it is not blocked on a speculative universal worktree API. The separate push-policy proposal does not alter its completion requirements.

## Acceptance and evidence matrix

| Requirement and formal scenario | Observable result | Evidence |
| --- | --- | --- |
| FMC-01 Main advanced | Helper chooses authenticated bound merge SHA, not current target HEAD | Real Git fixture with two later target commits and scoped SCM response |
| FMC-01 Object/identity unavailable | Actionable refusal before tracker mutation; no implicit fetch | Missing object and mismatched/unmerged PR cases |
| FMC-02 Dirty caller / Historical conflict | Caller HEAD/index/tracked/untracked content unchanged; conflicting historical identity refused | Before/after real filesystem/Git snapshots |
| FMC-02 Local state/input continuity | Relative input/state paths keep meaning; same journal and credentials resolve without secret copies | Explicit override cases and redacted temporary-resource inspection |
| FMC-03 Gates / No-spec / Handoff pending | Existing gates and result semantics unchanged | Existing finish regressions exercised through helper with mocked transports |
| FMC-04 Lost response / Concurrent invocations | Fresh reconciliation, stable correlation and no repeated confirmed transition | Fault-injection and concurrent temporary-repository cases |
| FMC-05 Normal / Changed resource / Foreign path | Owned clean resources removed; unsafe removal retained and reported separately | Real cleanup, refusal and failure-injection cases |
| TR-04 Recovery guidance | Plain finish still refuses wrong revision and offers explicit helper/manual remedy | CLI/service and generated-guidance regression |

All implementation evidence is pending. Mocked provider outcomes are not live completion qualification; an actual sandbox run must be separately authorized and recorded with its exact revision/environment.

## Implementation sequence

The [task list](tasks.md) is authoritative. First establish immutable resolution and caller-preservation cases; introduce a small shared helper behind the explicit CLI option. Then compose existing finish gates with local identity/state continuity. Add interruption/concurrency/cleanup cases before collecting local evidence. Update guidance, run required checks, archive/review/merge and finish through the same existing lifecycle the helper composes.

## Documentation impact

Review `docs/development-workflow.md`, `docs/workflows/tool-map.md`, selected-capability generated guidance, relevant work-service architecture mapping and `docs/verification/delivery-path-baseline.md`. Keep manual recovery available. Record actual observed command savings only after execution, update catalog mappings where affected and record content-bound dispositions. Do not add another completion report or manufacture live tracker evidence.

## Open inputs and next action

No unresolved merge semantics: the authenticated bound PR merge SHA is authoritative, and missing local objects produce a fetch remedy. Implementation must inspect the current platform-safe worktree/locking primitives and select bounded storage/recovery details that meet ownership requirements; it must not invent remote reconciliation. A future live sandbox host/credentials and implementation owner remain unassigned.

Decision: proceed with specification/issue handoff for this bounded helper, without extending it to pre-merge orchestration or executing provider mutations during specification preparation.
