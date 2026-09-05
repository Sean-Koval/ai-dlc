# Make selected project tools and guidance ready across machines Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when delegation is authorized. Steps use checkbox syntax for tracking.

**Goal:** Join selected provider requirements with machine provisioning and expose actionable project readiness without confusing it with release certification.

**Architecture:** Add ai-dlc project readiness --root PATH (read-only; exit 0 only when required checks are ready, else 1). Dimensions are tool, configuration, credential, guidance, and provider-health. Use catalog verify commands through a bounded injected probe; no installs/network for plain readiness, provider-health remains unverified unless existing explicit health inspection was requested through doctor. Provider-health is informational in offline readiness. Extend setup plan/apply and machine plan/apply with optional --root; root-aware planning unions declared modules with resolved component modules without editing the profile. Apply follows the existing explicit mutation command. Guidance readiness checks that the selected harness receives an index pointing to real configured-provider instructions. Existing root/machine doctor readiness contract is preserved, with the richer project report added under project_readiness.

**Tech Stack:** Python 3.12, existing AI-DLC CLI/services, Markdown workflow assets, OpenSpec, and configured tracker/SCM adapters. Reuse existing dependencies; any new dependency requires a documented necessity and explicit review.

**Spec:** [connected-project-readiness](../../../openspec/changes/connected-project-readiness/specs/connected-project-readiness/spec.md)

## Global constraints

No credential auto-loading, automatic account choice, new client support claim, hosted control plane, or weakening of existing doctor/finish behavior.

Milestone: M1. Dependencies: `component-capability-contract`.

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

inspect_readiness(root: Path, config: dict, *, environ: Mapping[str,str], probe: Callable[[list[str]],dict]) -> dict returns {schema:1, ready:bool, checks:[{component, dimension, status, reason, next_action}], qualification:'not-assessed'}. status is ready, missing, blocked, or unverified. Extend MachineManager.plan/apply with optional root: Path | None = None; omitted root retains current behavior.

### Files and ownership

- Create src/ai_dlc/readiness.py
- Modify src/ai_dlc/cli.py
- Modify src/ai_dlc/machine.py
- Modify src/ai_dlc/provision.py
- Modify src/ai_dlc/agents.py
- Test tests/test_readiness.py
- Modify tests/test_machine.py, tests/test_cli.py, tests/test_rendering.py

All listed source/test paths are relative to the repository root. New paths are proposed deliverables, not claims that those files exist today.

## First executable acceptance example

The following is a target regression, to be added during implementation. It is not run in this documentation change.

```python
from pathlib import Path
from ai_dlc.readiness import inspect_readiness

def test_missing_tool_reports_next_action(tmp_path: Path):
    result = inspect_readiness(tmp_path, {"roles": {"specs": "openspec"}}, environ={}, probe=lambda argv: {"available": False})
    gaps = [c for c in result["checks"] if c["dimension"] == "tool"]
    assert gaps and gaps[0]["status"] == "missing"
    assert gaps[0]["next_action"]
    assert result["ready"] is False
    assert result["qualification"] == "not-assessed"
```

Run it first and verify the failure is the missing specified behavior, then implement against the interfaces above.

Tests are introduced incrementally: Task 1 covers only its delivered boundary;
add later-task assertions when that task begins. Capture red then green within
each task. Do not commit a deliberately failing suite or make future behavior
pass with placeholders. The first acceptance example may span multiple tasks;
add it at the task that owns its complete interface.

### Task 1: Readiness model

**Files:** src/ai_dlc/readiness.py, tests/test_readiness.py plus the directly affected source/generated files listed above.

**Consumes:** The specification, fixtures/examples described above, and completed dependency interfaces.

**Produces:** Implement inspect_readiness with injected probes and tests for absent binary, absent guidance, absent environment key, valid offline requirements, and headless capability. Prove outputs never contain credential values. Keep provisioning and CLI exposure for Tasks 2 and 3.

- [ ] 1.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 1.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 1.3 Implement inspect_readiness with injected probes and tests for absent binary, absent guidance, absent environment key, valid offline requirements, and headless capability. Prove outputs never contain credential values. Keep provisioning and CLI exposure for Tasks 2 and 3.
- [ ] 1.4 Run `uv run --locked --no-sync pytest -q tests/test_readiness.py tests/test_machine.py tests/test_provision.py tests/test_cli.py tests/test_rendering.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 1.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 1.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 2: Root-aware setup

**Files:** src/ai_dlc/machine.py plus the directly affected source/generated files listed above.

**Consumes:** Task 1's committed artifacts and the shared interface contract above.

**Produces:** Forward optional root through public commands, manager, and provisioning; union modules using CC-01 and preserve explicit profile/machine precedence and no-root behavior.

- [ ] 2.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 2.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 2.3 Forward optional root through public commands, manager, and provisioning; union modules using CC-01 and preserve explicit profile/machine precedence and no-root behavior.
- [ ] 2.4 Run `uv run --locked --no-sync pytest -q tests/test_readiness.py tests/test_machine.py tests/test_provision.py tests/test_cli.py tests/test_rendering.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 2.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 2.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 3: Harness guidance and reporting

**Files:** src/ai_dlc/agents.py plus the directly affected source/generated files listed above.

**Consumes:** Task 2's committed artifacts and the shared interface contract above.

**Produces:** Render an owned provider/tool index into supported client guidance; implement project readiness and add diagnostics to doctor without overriding machine enrollment failures.

- [ ] 3.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 3.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 3.3 Render an owned provider/tool index into supported client guidance; implement project readiness and add diagnostics to doctor without overriding machine enrollment failures.
- [ ] 3.4 Run `uv run --locked --no-sync pytest -q tests/test_readiness.py tests/test_machine.py tests/test_provision.py tests/test_cli.py tests/test_rendering.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 3.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 3.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

## Requirement coverage

| Requirement / verification criterion | Tasks | Verification |
| --- | --- | --- |
| RD-01: Connected provisioning plan | 1, 2 | Focused positive and refusal cases, then integration and required project checks. |
| RD-02: Readiness is actionable and scoped | 1, 2, 3 | Focused positive and refusal cases, then integration and required project checks. |
| RD-03: Environment consistency preserves local identity | 2, 3 | Focused positive and refusal cases, then integration and required project checks. |

## Completion and handoff

- [ ] Run `ai-dlc project check --required`; inspect all five outcomes.
- [ ] Run `openspec validate connected-project-readiness --strict --no-interactive`, review against this plan, and archive only after all implementation tasks are complete. Update the work record to the exact archived path.
- [ ] Create/link the PR, complete review and required CI, and use `ai-dlc work finish connected-project-readiness` only after merge evidence exists.
- [ ] Leave a handoff with work/ticket ID, branch and revision, delivered interfaces, checks and evidence locations, unresolved findings, and the next dependency-unblocked ticket.

Stop and report a blocked task if a dependency is incomplete, an accepted interface conflicts with existing behavior, a required live environment is unavailable, or a required human label/budget is absent. Continue independent local preparation where possible. Do not invent missing product decisions or broaden scope to clear a blocker.
