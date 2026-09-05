# Calibrate UI/UX evaluation and measure its incremental value Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when delegation is authorized. Steps use checkbox syntax for tracking.

**Goal:** Measure when the optional design evaluator improves UI outcomes enough to justify its cost.

**Architecture:** Use original cases covering polished-but-broken, plain-but-usable, established-brand, keyboard failure, and screenshot-only candidates. Calibration and held-out assignments are frozen before tuning. A human supplies taste anchors and ratings. Declare a separate model/run budget before paid execution. Positive aesthetic scores cannot compensate for failed required journeys or absent evidence. Recommend retaining, simplifying, or removing the evaluator based on observed results.

**Tech Stack:** Python 3.12, existing AI-DLC CLI/services, Markdown workflow assets, OpenSpec, and configured tracker/SCM adapters. Reuse existing dependencies; any new dependency requires a documented necessity and explicit review.

**Spec:** No new formal behavior: this ticket verifies its predecessor contracts.

## Global constraints

No paid runs without a declared budget, fabricated human preference, broad client qualification, or claim that distribution tests prove design quality.

Milestone: M3. Dependencies: `design-pm-workflow`.

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

Consume candidate/rubric/report identity from design-pm-workflow. Compare baseline, rubric-only, and rubric-plus-independent-evaluation conditions. Preserve human labels, pairwise judgments, defect findings, time and usage, and held-out case identity.

### Files and ownership

- Create agents/evaluations/design-pm/protocol.md
- Create agents/evaluations/design-pm/cases.json
- Create docs/verification/design-pm-evaluation.md

All listed source/test paths are relative to the repository root. New paths are proposed deliverables, not claims that those files exist today.

## Behavioral review cases

For each criterion below, preserve the input, produced artifact or observation, expected result, actual result, and evidence. Packaging checks only prove asset delivery; they do not substitute for these cases.

- **DE-01 — Separate calibration evidence:** Original examples include behavioral defects and subjective disagreement; held-out cases are not used to tune the evaluator.
- **DE-02 — Incremental value comparison:** Matched baseline, rubric-only, and independent-evaluation runs report human preference, missed defects, false positives, cost, and time.
- **DE-03 — Honest completion:** Missing budget, human review, or browser access is reported; unavailable evidence does not qualify the workflow as improving design.

### Task 1: Prepare cases and human anchors

**Files:** agents/evaluations/design-pm/cases.json plus the directly affected source/generated files listed above.

**Consumes:** The specification, fixtures/examples described above, and completed dependency interfaces.

**Produces:** Create the original UI cases, identify known defects, and collect human score rationales without substituting model-written labels.

- [ ] 1.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 1.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 1.3 Create the original UI cases, identify known defects, and collect human score rationales without substituting model-written labels.
- [ ] 1.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 1.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 1.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 2: Freeze comparison protocol

**Files:** agents/evaluations/design-pm/protocol.md plus the directly affected source/generated files listed above.

**Consumes:** Task 1's committed artifacts and the shared interface contract above.

**Produces:** Declare the three conditions, repeated runs, versions, budget, evidence handling, and held-out split.

- [ ] 2.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 2.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 2.3 Declare the three conditions, repeated runs, versions, budget, evidence handling, and held-out split.
- [ ] 2.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 2.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 2.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 3: Evaluate and report

**Files:** docs/verification/design-pm-evaluation.md plus the directly affected source/generated files listed above.

**Consumes:** Task 2's committed artifacts and the shared interface contract above.

**Produces:** Run authorized experiments, compare candidate evidence and human judgments, and recommend the smallest effective workflow.

- [ ] 3.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 3.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 3.3 Run authorized experiments, compare candidate evidence and human judgments, and recommend the smallest effective workflow.
- [ ] 3.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 3.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 3.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

## Requirement coverage

| Requirement / verification criterion | Tasks | Verification |
| --- | --- | --- |
| DE-01: Separate calibration evidence | 1, 2 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| DE-02: Incremental value comparison | 1, 2, 3 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| DE-03: Honest completion | 2, 3 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |

## Completion and handoff

- [ ] Run `ai-dlc project check --required`; inspect all five outcomes.
- [ ] Create/link the PR, complete review and required CI, and use `ai-dlc work finish design-pm-calibration` only after merge evidence exists.
- [ ] Leave a handoff with work/ticket ID, branch and revision, delivered interfaces, checks and evidence locations, unresolved findings, and the next dependency-unblocked ticket.

Stop and report a blocked task if a dependency is incomplete, an accepted interface conflicts with existing behavior, a required live environment is unavailable, or a required human label/budget is absent. Continue independent local preparation where possible. Do not invent missing product decisions or broaden scope to clear a blocker.
