# Add optional UI/UX design generation and evaluation workflow Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when delegation is authorized. Steps use checkbox syntax for tracking.

**Goal:** Implement the existing Design PM proposal as an optional UI/UX workflow consuming a shaped product outcome and delivering evidence for its interaction criteria.

**Architecture:** Retain the current OpenSpec Design PM requirements. Implement two skills: design-brief creates the rubric and hands generation to the chosen existing visual tool/skill; design-evaluate inspects a running candidate or records static limitations. No new image generator or universal orchestrator. First sample defaults remain 0–4 scores, minimum 3 on required rated criteria, all required behavior checks pass, initial candidate plus at most two revision rounds; these are examples to review per task, not global gates. Existing design systems take precedence over novelty. A small UI fix may use one concise report.

**Tech Stack:** Python 3.12, existing AI-DLC CLI/services, Markdown workflow assets, OpenSpec, and configured tracker/SCM adapters. Reuse existing dependencies; any new dependency requires a documented necessity and explicit review.

**Spec:** [design-pm-workflow](../../../openspec/changes/design-pm-workflow/specs/design-pm/spec.md)

## Global constraints

No AI-DLC frontend, universal design score, mandatory evaluator for every task, inferred human review, or new completion gate.

Milestone: M2. Dependencies: `product-shaping-workflow`, `spec-delivery-traceability`.

## Execution contract

- Read AGENTS.md, ai-dlc.toml, the current work record, docs/product-direction.md, the [shared implementation clarifications](../../design/framework-delivery.md#frozen-cross-ticket-contracts), and this ticket's specification (or predecessor contracts for verification work) before edits.
- Prepare the checkout with `sh scripts/bootstrap.sh --source` and use its printed PATH. Work on the ticket's own branch after the planning branch is integrated.
- Dependencies below must be completed and their artifacts available. Until TR-02 is implemented, check their tracker state and accepted evidence manually; do not add unsupported fields to the current Work schema.
- Keep each requirement's implementation, tests, source documentation, and generated assets in the same change. Preserve unrelated edits and legacy Rust source.
- Use existing native tools directly where appropriate. Existing repository checks and `ai-dlc work finish` remain the completion boundary.
- For implementation of skills, read the installed skill-authoring instructions at execution time; do not change only generated .agents/.claude copies. For code, demonstrate each new observable failure with a focused regression before implementation.
- Every task ends with its focused checks and a conventional commit. Final review requires `ai-dlc project check --required` and strict OpenSpec validation for behavior tickets.
- A published backlog ticket is not completed implementation. Never tick tasks merely because a plan, template, or mocked result exists.

## Scope and interfaces

Input is a PS product brief and TR delivery slice with RQ IDs. Output is the existing docs/design/<work-id>/ brief/rubric/iterations/decision artifact contract. Criterion IDs are local to a versioned rubric and reference relevant RQ IDs. Findings reference candidate revision, criterion, observed state, evidence, severity, and next action.

### Files and ownership

- Create agents/skills/design-brief/SKILL.md
- Create agents/skills/design-evaluate/SKILL.md
- Create agents/templates/design-rubric.md, design-evaluation.md and design-selection.md
- Create agents/examples/design-evaluation/
- Update agents/skills.lock.json and generated copies
- Modify docs/workflows/design-to-implementation.md and matching project templates
- Test tests/test_templates.py, tests/test_rendering.py

All listed source/test paths are relative to the repository root. New paths are proposed deliverables, not claims that those files exist today.

## Behavioral review cases

For each criterion below, preserve the input, produced artifact or observation, expected result, actual result, and evidence. Packaging checks only prove asset delivery; they do not substitute for these cases.

- **UI-01 — Candidate contract:** A static candidate leaves interaction checks unverified; a failed required journey blocks acceptance regardless of aesthetics.
- **UI-02 — Proportional effort:** A small brand-constrained fix uses existing components and a concise report without inventing a new visual direction.
- **UI-03 — Revision selection:** A regressed later candidate can be rejected in favor of the earlier candidate with matching evidence.

### Task 1: Rubric and evaluator examples

**Files:** agents/examples/design-evaluation/ plus the directly affected source/generated files listed above.

**Consumes:** The specification, fixtures/examples described above, and completed dependency interfaces.

**Produces:** Use the shaped product brief; add criterion-specific score anchors and examples of attractive-but-broken, brand-consistent, and unverified static outputs.

- [ ] 1.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 1.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 1.3 Use the shaped product brief; add criterion-specific score anchors and examples of attractive-but-broken, brand-consistent, and unverified static outputs.
- [ ] 1.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py tests/test_rendering.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 1.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 1.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 2: Portable skills and artifact handoff

**Files:** agents/skills/design-evaluate/SKILL.md plus the directly affected source/generated files listed above.

**Consumes:** Task 1's committed artifacts and the shared interface contract above.

**Produces:** Implement design-brief/design-evaluate with independent-session or human fallback, reproducible findings, revision/plateau rules, and earlier-candidate selection.

- [ ] 2.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 2.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 2.3 Implement design-brief/design-evaluate with independent-session or human fallback, reproducible findings, revision/plateau rules, and earlier-candidate selection.
- [ ] 2.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py tests/test_rendering.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 2.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 2.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 3: Integration and packaging

**Files:** tests/test_templates.py plus the directly affected source/generated files listed above.

**Consumes:** Task 2's committed artifacts and the shared interface contract above.

**Produces:** Connect the optional route from product shaping, ship templates/examples, verify owned updates and clearly leave live quality improvement pending.

- [ ] 3.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 3.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 3.3 Connect the optional route from product shaping, ship templates/examples, verify owned updates and clearly leave live quality improvement pending.
- [ ] 3.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py tests/test_rendering.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 3.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 3.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

## Requirement coverage

| Requirement / verification criterion | Tasks | Verification |
| --- | --- | --- |
| DP-01: Design intent precedes evaluation | 1, 2 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| DP-02: Evaluation preserves evidence and uncertainty | 2 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| DP-03: Independent review is explicit | 2 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| DP-04: Iteration respects budgets and candidate identity | 2 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| DP-05: Guidance travels through existing project distribution | 3 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| DP-06: Calibration claims require measured evidence | 1, 3 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |

## Completion and handoff

- [ ] Run `ai-dlc project check --required`; inspect all five outcomes.
- [ ] Run `openspec validate design-pm-workflow --strict --no-interactive`, review against this plan, and archive only after all implementation tasks are complete. Update the work record to the exact archived path.
- [ ] Create/link the PR, complete review and required CI, and use `ai-dlc work finish design-pm-workflow` only after merge evidence exists.
- [ ] Leave a handoff with work/ticket ID, branch and revision, delivered interfaces, checks and evidence locations, unresolved findings, and the next dependency-unblocked ticket.

Stop and report a blocked task if a dependency is incomplete, an accepted interface conflicts with existing behavior, a required live environment is unavailable, or a required human label/budget is absent. Continue independent local preparation where possible. Do not invent missing product decisions or broaden scope to clear a blocker.
