# Evaluate product shaping and delivery guidance against baseline behavior Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when delegation is authorized. Steps use checkbox syntax for tracking.

**Goal:** Measure whether the general product-to-delivery guidance improves decisions, scope control, and implementation handoff using human-labeled scenarios.

**Architecture:** Prepare six original cases: ambiguous new product, unvalidated feature request, contradictory requirements, legacy compatibility change, risky migration, and tiny mechanical fix. Use four for calibration and hold back two until prompts are frozen. Compare existing guidance with revised guidance on matched inputs and equal declared budgets. Report decision accuracy, invented facts, unjustified scope growth, missing behavior/verification links, and human usefulness ratings. Record a dedicated approved budget before paid runs. Existing agents/evaluation.toml remains its own pending release gate and must not be relabeled completed by this smaller experiment.

**Tech Stack:** Python 3.12, existing AI-DLC CLI/services, Markdown workflow assets, OpenSpec, and configured tracker/SCM adapters. Reuse existing dependencies; any new dependency requires a documented necessity and explicit review.

**Spec:** No new formal behavior: this ticket verifies its predecessor contracts.

## Global constraints

No fabricated human ratings, automatic paid experiments, universal quality claims, or substitution for existing release evaluations.

Milestone: M3. Dependencies: `product-shaping-workflow`, `spec-delivery-traceability`.

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

Each case records id, mode (greenfield/brownfield), prompt, evidence, material_unknowns, expected_decisions, disallowed_assumptions, requirement_ids, and held_out. Each run records exact asset/model versions, condition, actual usage/time, transcript, human judgments, and missing evidence.

### Files and ownership

- Create agents/evaluations/product-delivery/protocol.md
- Create agents/evaluations/product-delivery/cases.json
- Create docs/verification/product-delivery-evaluation.md
- Update docs/release-verification.md

All listed source/test paths are relative to the repository root. New paths are proposed deliverables, not claims that those files exist today.

## Behavioral review cases

For each criterion below, preserve the input, produced artifact or observation, expected result, actual result, and evidence. Packaging checks only prove asset delivery; they do not substitute for these cases.

- **EV-01 — Original labeled cases:** Cases distinguish evidence from assumptions, cover both entry paths, and include correct investigate/stop/no-spec outcomes.
- **EV-02 — Controlled comparison:** Comparison uses fixed recorded versions/budgets and held-out cases; full transcripts and actual costs/time are preserved where available.
- **EV-03 — Human-grounded claims:** Human labels are supplied by humans; absent ratings remain pending, and results state observed scope without asserting universal model improvement.

### Task 1: Case and rubric preparation

**Files:** agents/evaluations/product-delivery/cases.json plus the directly affected source/generated files listed above.

**Consumes:** The specification, fixtures/examples described above, and completed dependency interfaces.

**Produces:** Create six cases and score keys; identify which judgments require humans and freeze the two held-out cases before prompt tuning.

- [ ] 1.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 1.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 1.3 Create six cases and score keys; identify which judgments require humans and freeze the two held-out cases before prompt tuning.
- [ ] 1.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 1.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 1.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 2: Comparison protocol

**Files:** agents/evaluations/product-delivery/protocol.md plus the directly affected source/generated files listed above.

**Consumes:** Task 1's committed artifacts and the shared interface contract above.

**Produces:** Record conditions, model/budget selection, repetitions, order balancing, transcript storage, and the decision metrics before execution.

- [ ] 2.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 2.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 2.3 Record conditions, model/budget selection, repetitions, order balancing, transcript storage, and the decision metrics before execution.
- [ ] 2.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 2.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 2.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 3: Run and review evidence

**Files:** docs/verification/product-delivery-evaluation.md plus the directly affected source/generated files listed above.

**Consumes:** Task 2's committed artifacts and the shared interface contract above.

**Produces:** After the budget and human participation are available, run comparisons and publish results including negative outcomes, disagreements, and limitations.

- [ ] 3.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 3.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 3.3 After the budget and human participation are available, run comparisons and publish results including negative outcomes, disagreements, and limitations.
- [ ] 3.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 3.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 3.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

## Requirement coverage

| Requirement / verification criterion | Tasks | Verification |
| --- | --- | --- |
| EV-01: Original labeled cases | 1, 2 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| EV-02: Controlled comparison | 1, 2, 3 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| EV-03: Human-grounded claims | 2, 3 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |

## Completion and handoff

- [ ] Run `ai-dlc project check --required`; inspect all five outcomes.
- [ ] Create/link the PR, complete review and required CI, and use `ai-dlc work finish workflow-quality-calibration` only after merge evidence exists.
- [ ] Leave a handoff with work/ticket ID, branch and revision, delivered interfaces, checks and evidence locations, unresolved findings, and the next dependency-unblocked ticket.

Stop and report a blocked task if a dependency is incomplete, an accepted interface conflicts with existing behavior, a required live environment is unavailable, or a required human label/budget is absent. Continue independent local preparation where possible. Do not invent missing product decisions or broaden scope to clear a blocker.
