# Delivery slice: behavioral-check-onboarding

Proposed local work ID: `behavioral-check-onboarding`. Priority: P1.
Owner: Sean Koval, product decision; implementation owner unassigned.
Status: specification and issue preparation authorized; implementation not started.
Review source: September 26 team-adoption review and the user's request to specify and create issues. This does not imply implementation approval, live qualification or paid evaluation authorization.
Canonical brief authority: [product direction](../../../docs/product-direction.md). Review trace: OUT-001, RQ-004 and RQ-005 (team adoption); formal acceptance resides in this change.

## Problem and outcome

An adopting team can preserve its own test tools yet still lack an observed link between a requirement and a meaningful check. The normal runner's mise dependency can also surprise a generic project or source-candidate evaluation. Deliver a short guided path from inspection to reviewed commands and one safely demonstrated behavioral regression, using existing setup/check services.

## Scope and exclusions

Include source-grounded command selection, explicit prerequisite review, normal-runner readiness, isolated passing/failing/restored-passing evidence and honest focused/full-check distinctions. Preserve existing tests, shells, required checks and receipts. Exclude a new testing framework, automatic quality scoring, active-worktree sabotage, production/remote mutations, a general onboarding wizard, paid comparisons and claims of Windows or native-client qualification from local fixtures.

## Specification decision

requires_spec: true.
spec_reason: Adds observable adopter guidance and verification evidence requirements while preserving the existing runner and receipt contracts.
Formal source: [portable-development delta](specs/portable-development/spec.md).
Requirements: BCO-01, BCO-02, BCO-03, BCO-04, BCO-05. Existing compatibility requirements: PC-01, PC-02, PC-03 and RD-04.

## Dependencies and interfaces

depends_on: [] — independently finishable against existing project setup/check and image-preparation services. No other proposed team-adoption change is a hard dependency. Existing interface sources are `src/ai_dlc/setup/project.py`, `src/ai_dlc/setup/readiness.py`, `src/ai_dlc/providers/scm.py`, `src/ai_dlc/verification/evaluation/image.py`, and the canonical portable-development/connected-project-readiness specifications. Their implementation is observed at review revision 3d4ffc1; this document does not assert fresh remote completion status.

Consumer onboarding may link this guidance when delivered. Native Windows evidence belongs to its own platform work and does not block demonstrating the existing supported local runner. Candidate-image readiness is a prerequisite for any later #138 comparison, but #138 execution is not a dependency or an authorized task here.

## Acceptance and evidence matrix

| Requirement and formal scenario | Observable result | Evidence and boundary |
| --- | --- | --- |
| BCO-01 Existing team tests / No behavioral check | Inspection cites actual sources and either maps a requirement or retains uncertainty | Guidance fixtures and one inspected sample; no adequacy claim |
| BCO-02 Maintainer accepts / Setup unaccepted | Only reviewed commands enter existing services; authored content retained | Existing-project filesystem tests and command trace |
| BCO-03 Generic project lacks mise | Structured unavailable-runtime output, no executed check or receipt | Missing-runtime fixture with empty tools |
| BCO-03 Candidate preparation | Ordinary required runner succeeds after declared common runtime preparation | Real offline source-candidate image smoke; no model calls; separate from cross-platform/native qualification |
| BCO-04 Regression / Not detected / Isolation refused | Pass/fail/restored pass, or explicit incomplete evidence; active tree unchanged | Real disposable local fixture plus negative containment cases |
| BCO-05 Focused feedback | Partial receipt never completes missing required outcomes | Existing receipt regressions plus complete required run |

All implementation evidence is pending. A successful fixture or candidate smoke cannot fill the native-Windows, human-quality or paid-comparison columns.

## Implementation sequence

The [task list](tasks.md) is authoritative. First establish preservation and guidance cases, then implement the smallest existing guidance surface. Next clarify and prepare runtime prerequisites, rehearse the actual behavioral check in isolation, and retain bounded evidence. Review documentation, run focused and required checks, archive/review/merge and finish through the existing lifecycle. Do not repeat the task checklist in the issue body.

## Documentation impact

Review `docs/development-workflow.md`, existing brownfield adoption guidance, `docs/verification/end-to-end-evaluation.md`, and relevant packaged skill/template guidance. Update `docs/catalog.toml` mappings when their source dependencies change and record current content-bound dispositions. Keep fixture logs ignored locally and durable reviewed evidence in the existing verification owner. Product-direction wording needs review, not a speculative success claim.

## Open inputs and next action

The adopting maintainer supplies one real requirement, test command and safe representative fixture; those are project inputs, not a reason to add a default framework. Implementation chooses the smallest existing guidance asset after inspecting its current ownership. Available candidate-build resources and native platform hosts must be reported honestly. Paid #138 execution remains explicitly deferred.

Decision: proceed with the reviewed specification/issue handoff; implementation starts only through its assigned delivery task. Validation reported by the author concerns this specification package, not implemented acceptance.
