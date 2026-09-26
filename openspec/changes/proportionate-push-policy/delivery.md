# Delivery slice: proportionate-push-policy

Proposed local work ID: `proportionate-push-policy`. Priority: P1.
Owner: Sean Koval, product decision; implementation owner unassigned.
Status: specification and issue preparation authorized; implementation not started.
Review source: September 26 team-adoption review and the user's request to specify and create issues, including explicit lightweight policy with strict default preserved.
Canonical brief authority: [product direction](../../../docs/product-direction.md). Review trace: OUT-001 and RQ-005; formal acceptance resides in this change.

## Problem and outcome

Teams selecting optional bound-push protection cannot use the canonical no-record PR path because its current hook requires a reviewed tracker-bound record on every covered publication. Add a deliberate project choice that permits truly unbound branches while retaining validation of every associated work record. Several valid work items may legitimately share a delivery branch and must continue to work.

## Scope and exclusions

Add `[agents] bound_push_policy` with `all-branches` default and explicit `tracked-branches` mode. Keep project ownership, supported native-hook coverage, destructive denials and all completion gates. Exclude machine-local waivers, a per-branch exception store, automatic tracker creation, remote pre-tool lookups, new hook platforms, diff/branch-size heuristics and implicit removal of existing policy.

## Specification decision

requires_spec: true.
spec_reason: Adds a public project configuration field and observable hook/guidance behavior for an explicit lightweight workflow.
Formal source: [native-work-harnesses delta](specs/native-work-harnesses/spec.md).
Requirements: PPP-01, PPP-02, PPP-03, PPP-04. Existing native capability/coverage and completion contracts are preserved.

## Dependencies and interfaces

depends_on: [] — this is independently finishable against existing configuration, local work validation and hook rendering. Interface sources: `src/ai_dlc/config.py`, `src/ai_dlc/harness/hooks.py`, `src/ai_dlc/harness/agents.py`, `src/ai_dlc/work/workflow.py` and `agents/capabilities.toml`. Existing implementation was inspected at 3d4ffc1; fresh tracker status is not asserted here.

No new native qualification is claimed by the offline policy delivery. Platform-specific hook availability stays governed by the current client/version capability contract. Other team-adoption changes can consume the policy but are not required for this issue to finish.

## Acceptance and evidence matrix

| Requirement and scenario | Observable result | Evidence |
| --- | --- | --- |
| PPP-01 Omitted policy / Explicit opt-in | Strict default unchanged; only valid project field selects lightweight mode | Config and rendering tests |
| PPP-01 Local/imported waiver | Personal, machine and team-source input rejected | Layer ownership tests |
| PPP-02 Record not ready / Incomplete association | Invalid matching record or unreadable inventory denies, without remote probes | Real Git fixture and prohibited-provider/journal assertions |
| PPP-02 Several valid work items | Every matching record validated; multiple valid records remain allowed in either mode | Multi-record regression fixture, then one-invalid-member case |
| PPP-03 Unbound branch / Apparent small change | Truly unbound allowed only by opt-in; tracked invalid documentation change still denied | Direct git-push and PR-create payload cases |
| PPP-03 Force push | Existing destructive denial persists | Classifier/service regression |
| PPP-04 Guidance / Hook unselected | Policy-specific prose matches behavior; setting does not enable hooks | Deterministic generation tests and authored-content preservation |

Evidence is planned, not executed implementation qualification. Local payload fixtures do not establish full client walkthrough coverage.

## Implementation sequence

The [task list](tasks.md) owns implementation steps. Define the project field and rejection boundaries first, then implement complete offline association classification. Add explicit lightweight allowance only after invalid/multiple-record regression cases are pinned. Update applicable guidance and examples, collect bounded service evidence, then run required checks and complete normal archived-spec delivery.

## Documentation impact

Review `docs/development-workflow.md`, `docs/workflows/tool-map.md`, applicable machine/client runbooks, generated shared guidance and configuration examples. Explain both strict and lightweight behavior without claiming hook enforcement outside recognized payloads. Update affected `docs/catalog.toml` mappings and current content-bound dispositions. No second workflow handbook is needed.

## Open inputs and next action

The configuration field, modes and strict default are specified here; there is no unresolved per-branch exemption design. Each team maintainer decides whether to opt in through shared project review. An implementation owner must inspect available offline validation helpers and ensure they do not instantiate journals/providers during a hook. Actual installed-client versions remain independent qualification inputs.

Decision: proceed with specification/issue handoff. Do not change any existing project's mode during implementation tests or treat this issue's creation as authorization to weaken its policy.
