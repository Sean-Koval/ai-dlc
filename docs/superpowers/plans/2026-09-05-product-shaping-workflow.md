# Guide product discovery and feature selection for new and existing products Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when delegation is authorized. Steps use checkbox syntax for tracking.

**Goal:** Give agents concrete guidance and examples for choosing worthwhile product increments before writing specifications or code.

**Architecture:** Reuse existing discovery/PRD/inbox skills; do not create a competing PM lifecycle. Greenfield compares at least two feasible approaches plus doing nothing when meaningful. Brownfield records actual behavior, constraints, affected users, compatibility, and rollback needs. Separate user evidence from model hypotheses. Make priority a reasoned judgment using user impact, confidence in evidence, effort, and dependencies without fabricated numeric precision. UI exploration is optional and routes to design-pm-workflow only when the slice changes an interface. Small work can use a single brief; no mandatory PRD/design/ticket duplication.

**Tech Stack:** Python 3.12, existing AI-DLC CLI/services, Markdown workflow assets, OpenSpec, and configured tracker/SCM adapters. Reuse existing dependencies; any new dependency requires a documented necessity and explicit review.

**Spec:** [product-shaping-workflow](../../../openspec/changes/product-shaping-workflow/specs/product-shaping-workflow/spec.md)

## Global constraints

No invented interviews or user approval, automatic ticket publication during discovery, mandatory UI work, replacement specification system, or broad autonomous feature expansion.

Milestone: M2. Dependencies: none; ready after the planning branch is integrated.

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

The product brief is Markdown with stable sections: Audience and problem; Evidence and assumptions; Current behavior (brownfield); Options and trade-offs; Selected outcome; Scope and exclusions; Success evidence; Next slice; Unresolved decisions. Requirement IDs use RQ-001 style within the brief; one canonical brief owns those IDs. Output ends with proceed, investigate, or stop plus reasons, not an invented approval.

### Files and ownership

- Modify agents/skills/discovery/SKILL.md
- Modify agents/skills/prd-draft/SKILL.md
- Modify agents/skills/review-inbox/SKILL.md
- Modify agents/templates/prd.md
- Create agents/templates/product-brief.md
- Create agents/examples/product-shaping/greenfield.md and brownfield.md
- Update agents/skills.lock.json and managed/generated copies
- Modify docs/workflows/greenfield.md, brownfield.md and matching project templates
- Test tests/test_templates.py and tests/test_rendering.py

All listed source/test paths are relative to the repository root. New paths are proposed deliverables, not claims that those files exist today.

## Behavioral review cases

For each criterion below, preserve the input, produced artifact or observation, expected result, actual result, and evidence. Packaging checks only prove asset delivery; they do not substitute for these cases.

- **PS-01 — Evidence-based product shaping:** The workflow SHALL distinguish observed evidence, user decisions, and hypotheses; it SHALL compare feasible options and identify a bounded outcome before proposing implementation.
- **PS-02 — Separate greenfield and brownfield entry paths:** Greenfield guidance SHALL shape the smallest useful outcome; brownfield guidance SHALL inspect existing behavior and preserve explicit compatibility boundaries.
- **PS-03 — Proportional handoff:** The workflow SHALL produce traceable outcome/requirement IDs and an explicit proceed, investigate, or stop decision; material unknowns SHALL remain visible and SHALL NOT become invented acceptance facts.

### Task 1: Worked examples and review criteria

**Files:** agents/examples/product-shaping/ plus the directly affected source/generated files listed above.

**Consumes:** The specification, fixtures/examples described above, and completed dependency interfaces.

**Produces:** Author one greenfield task and one brownfield task with evidence, options, excluded scope, RQ IDs, and a correct next action. Include a misleading feature request and contradictory requirements.

- [ ] 1.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 1.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 1.3 Author one greenfield task and one brownfield task with evidence, options, excluded scope, RQ IDs, and a correct next action. Include a misleading feature request and contradictory requirements.
- [ ] 1.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py tests/test_rendering.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 1.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 1.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 2: Skills and templates

**Files:** agents/skills/discovery/SKILL.md plus the directly affected source/generated files listed above.

**Consumes:** Task 1's committed artifacts and the shared interface contract above.

**Produces:** Update the existing skills and PRD template using the examples; include exact output sections and decision rules. Follow skill-authoring guidance during implementation and retain upstream-provider routing.

- [ ] 2.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 2.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 2.3 Update the existing skills and PRD template using the examples; include exact output sections and decision rules. Follow skill-authoring guidance during implementation and retain upstream-provider routing.
- [ ] 2.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py tests/test_rendering.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 2.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 2.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 3: Distribution and behavioral cases

**Files:** tests/test_templates.py plus the directly affected source/generated files listed above.

**Consumes:** Task 2's committed artifacts and the shared interface contract above.

**Produces:** Regenerate digest locks/client copies/templates; add packaging tests for assets and behavioral scenarios measuring decisions rather than just headings.

- [ ] 3.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 3.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 3.3 Regenerate digest locks/client copies/templates; add packaging tests for assets and behavioral scenarios measuring decisions rather than just headings.
- [ ] 3.4 Run `uv run --locked --no-sync pytest -q tests/test_templates.py tests/test_rendering.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 3.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 3.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

## Requirement coverage

| Requirement / verification criterion | Tasks | Verification |
| --- | --- | --- |
| PS-01: Evidence-based product shaping | 1, 2 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| PS-02: Separate greenfield and brownfield entry paths | 1, 2, 3 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| PS-03: Proportional handoff | 2, 3 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |

## Completion and handoff

- [ ] Run `ai-dlc project check --required`; inspect all five outcomes.
- [ ] Run `openspec validate product-shaping-workflow --strict --no-interactive`, review against this plan, and archive only after all implementation tasks are complete. Update the work record to the exact archived path.
- [ ] Create/link the PR, complete review and required CI, and use `ai-dlc work finish product-shaping-workflow` only after merge evidence exists.
- [ ] Leave a handoff with work/ticket ID, branch and revision, delivered interfaces, checks and evidence locations, unresolved findings, and the next dependency-unblocked ticket.

Stop and report a blocked task if a dependency is incomplete, an accepted interface conflicts with existing behavior, a required live environment is unavailable, or a required human label/budget is absent. Continue independent local preparation where possible. Do not invent missing product decisions or broaden scope to clear a blocker.
