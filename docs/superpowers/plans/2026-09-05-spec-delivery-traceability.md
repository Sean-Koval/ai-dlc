# Carry product requirements into independently deliverable specifications and tickets Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when delegation is authorized. Steps use checkbox syntax for tracking.

**Goal:** Give an executing agent an unambiguous connection from outcome to behavioral scenario, ticket, implementation step, and verification evidence.

**Architecture:** New work records list dependency work IDs, requirement IDs, exact artifact references, and acceptance/verification text. Validate missing referenced local records, self-dependency, cycles, unsafe IDs, and absent local artifacts before publication. Dependency validation verifies graph integrity; it does not claim dependencies completed. work start checks dependency tracker state and fails explicitly on unfinished or unavailable dependencies; a terminal cancelled/duplicate item does not satisfy a completion dependency. Existing records with empty lists keep their current behavior. The native publish body includes scope, requirements, dependencies, artifacts, and acceptance plus the unchanged correlation marker. Re-publishing an already linked item remains idempotent and does not silently overwrite authored remote descriptions. Spec guidance creates one independently finishable OpenSpec change per behavior ticket; OpenSpec tasks are steps inside that ticket, not one ticket per checkbox. A shared parent epic has no completion gate over child specs.

**Tech Stack:** Python 3.12, existing AI-DLC CLI/services, Markdown workflow assets, OpenSpec, and configured tracker/SCM adapters. Reuse existing dependencies; any new dependency requires a documented necessity and explicit review.

**Spec:** [spec-delivery-traceability](../../../openspec/changes/spec-delivery-traceability/specs/spec-delivery-traceability/spec.md)

## Global constraints

No automatic scope approval, duplicate spec store, spec-to-one-checkbox-ticket mapping, remote priority inference, or weakened finish gates.

Milestone: M2. Dependencies: `product-shaping-workflow`.

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

Add optional Work fields depends_on: list[str]=[] and requirements: list[str]=[]. Add validate_work_graph(records:dict[str,dict])->list[str] and render_ticket_body(work:dict)->str in traceability.py. Requirements are stable brief/spec requirement identifiers, not duplicated spec prose. Add ai-dlc work validate WORK_ID --root PATH (read-only, 0 valid/1 invalid). No automated interpretation of arbitrary natural-language specifications.

### Files and ownership

- Modify agents/skills/spec-from-prd/SKILL.md
- Create agents/templates/delivery-slice.md
- Modify src/ai_dlc/workflow.py
- Modify src/ai_dlc/cli.py
- Create src/ai_dlc/traceability.py
- Test tests/test_traceability.py
- Modify tests/test_workflow.py, tests/test_cli.py
- Update docs/workflows/design-to-implementation.md and generated templates

All listed source/test paths are relative to the repository root. New paths are proposed deliverables, not claims that those files exist today.

## First executable acceptance example

The following is a target regression, to be added during implementation. It is not run in this documentation change.

```python
from ai_dlc.traceability import validate_work_graph

def test_dependency_cycle_is_reported():
    records = {"a": {"id": "a", "depends_on": ["b"]}, "b": {"id": "b", "depends_on": ["a"]}}
    errors = validate_work_graph(records)
    assert any("cycle" in error.lower() for error in errors)
```

Run it first and verify the failure is the missing specified behavior, then implement against the interfaces above.

Tests are introduced incrementally: Task 1 covers only its delivered boundary;
add later-task assertions when that task begins. Capture red then green within
each task. Do not commit a deliberately failing suite or make future behavior
pass with placeholders. The first acceptance example may span multiple tasks;
add it at the task that owns its complete interface.

### Task 1: Pure graph validation and ticket rendering

**Files:** src/ai_dlc/traceability.py, tests/test_traceability.py plus the directly affected source/generated files listed above.

**Consumes:** The specification, fixtures/examples described above, and completed dependency interfaces.

**Produces:** Implement validate_work_graph and render_ticket_body with missing ID, self/cycle, stable order and rich body cases. Preserve correlation values. Task 2 owns optional Work fields, filesystem artifact checks and mutation ordering; the pure graph function does not inspect files or services.

- [ ] 1.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 1.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 1.3 Implement validate_work_graph and render_ticket_body with missing ID, self/cycle, stable order and rich body cases. Preserve correlation values. Task 2 owns optional Work fields, filesystem artifact checks and mutation ordering; the pure graph function does not inspect files or services.
- [ ] 1.4 Run `uv run --locked --no-sync pytest -q tests/test_traceability.py tests/test_workflow.py tests/test_cli.py tests/test_templates.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 1.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 1.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 2: Workflow integration

**Files:** src/ai_dlc/workflow.py plus the directly affected source/generated files listed above.

**Consumes:** Task 1's committed artifacts and the shared interface contract above.

**Produces:** Validate before mutation, expose work validate, check dependency completion before branch/start effects, and render richer descriptions on first create only.

- [ ] 2.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 2.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 2.3 Validate before mutation, expose work validate, check dependency completion before branch/start effects, and render richer descriptions on first create only.
- [ ] 2.4 Run `uv run --locked --no-sync pytest -q tests/test_traceability.py tests/test_workflow.py tests/test_cli.py tests/test_templates.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 2.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 2.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 3: Spec and task handoff guidance

**Files:** agents/skills/spec-from-prd/SKILL.md plus the directly affected source/generated files listed above.

**Consumes:** Task 2's committed artifacts and the shared interface contract above.

**Produces:** Update skill/template examples using PS requirement IDs; show an independently finishable change and a no-spec verification item; regenerate owned copies.

- [ ] 3.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 3.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 3.3 Update skill/template examples using PS requirement IDs; show an independently finishable change and a no-spec verification item; regenerate owned copies.
- [ ] 3.4 Run `uv run --locked --no-sync pytest -q tests/test_traceability.py tests/test_workflow.py tests/test_cli.py tests/test_templates.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 3.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 3.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

## Requirement coverage

| Requirement / verification criterion | Tasks | Verification |
| --- | --- | --- |
| TR-01: Explicit traceability | 1, 2 | Focused positive and refusal cases, then integration and required project checks. |
| TR-02: Valid dependency graph | 1, 2, 3 | Focused positive and refusal cases, then integration and required project checks. |
| TR-03: Compatible rich publication | 2, 3 | Focused positive and refusal cases, then integration and required project checks. |

## Completion and handoff

- [ ] Run `ai-dlc project check --required`; inspect all five outcomes.
- [ ] Run `openspec validate spec-delivery-traceability --strict --no-interactive`, review against this plan, and archive only after all implementation tasks are complete. Update the work record to the exact archived path.
- [ ] Create/link the PR, complete review and required CI, and use `ai-dlc work finish spec-delivery-traceability` only after merge evidence exists.
- [ ] Leave a handoff with work/ticket ID, branch and revision, delivered interfaces, checks and evidence locations, unresolved findings, and the next dependency-unblocked ticket.

Stop and report a blocked task if a dependency is incomplete, an accepted interface conflicts with existing behavior, a required live environment is unavailable, or a required human label/budget is absent. Continue independent local preparation where possible. Do not invent missing product decisions or broaden scope to clear a blocker.
