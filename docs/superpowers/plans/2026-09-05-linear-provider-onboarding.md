# Discover and safely configure a project's Linear connection Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when delegation is authorized. Steps use checkbox syntax for tracking.

**Goal:** Replace manual team/status UUID hunting with explicit, read-only discovery and a reviewed local configuration update.

**Architecture:** Add ai-dlc provider connect PROVIDER --root PATH. Without selection flags it prints complete discovery and exits without writes. Preview flags are --organization UUID --team UUID --in-progress UUID --closed UUID; --apply additionally writes local shared non-secret mappings. Use existing token_env; do not create or rotate keys. Validate selected team belongs to the selected organization result, started/completed state types and team membership. Multiple states are always listed; never infer In Progress from first started state. Paginate all selected discovery collections or fail incomplete. Preserve unrelated TOML content using a reviewed TOML editing approach; tests must assert comments and unrelated values survive. Refuse changed existing mappings when local work is already bound; point to explicit rebind. Preview can save its non-secret plan with --plan-file PATH under .ai-dlc/local. Apply consumes --plan-file PATH with --apply, revalidates selections against fresh discovery, and checks before_digest immediately before the atomic write; it never silently recomputes a different approved plan.

**Tech Stack:** Python 3.12, existing AI-DLC CLI/services, Markdown workflow assets, OpenSpec, and configured tracker/SCM adapters. Reuse existing dependencies; any new dependency requires a documented necessity and explicit review.

**Spec:** [linear-provider-onboarding](../../../openspec/changes/linear-provider-onboarding/specs/linear-provider-onboarding/spec.md)

## Global constraints

No API-key creation, Linear Project creation, issue mutation, organization switching, or automatic rebind. Use existing sandbox only for authorized live reads.

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

discover_linear(settings: dict, *, environ: Mapping[str,str], client) -> dict returns {organization:{id,name,urlKey}, teams:[{id,name,key,states:[{id,name,type}]}]}. plan_linear_connection(config:dict, discovery:dict, selection:dict) -> dict returns {provider, before_digest, selected, patch}; selection requires organization_id, team_id, in_progress, closed. apply_linear_connection(path:Path, plan:dict) verifies the before digest and atomically replaces only selected provider settings.

### Files and ownership

- Create src/ai_dlc/provider_onboarding.py
- Modify src/ai_dlc/providers/linear.py
- Modify src/ai_dlc/cli.py
- Test tests/test_provider_onboarding.py
- Modify tests/test_cli.py, tests/test_rebind.py

All listed source/test paths are relative to the repository root. New paths are proposed deliverables, not claims that those files exist today.

## First executable acceptance example

The following is a target regression, to be added during implementation. It is not run in this documentation change.

```python
import pytest
from ai_dlc.provider_onboarding import plan_linear_connection

def test_state_from_another_team_is_rejected():
    discovery = {"organization": {"id": "org"}, "teams": [{"id": "team", "states": [{"id": "done", "type": "completed"}]}]}
    with pytest.raises(ValueError):
        plan_linear_connection({"providers": {"linear": {}}}, discovery, {"organization_id": "org", "team_id": "team", "in_progress": "foreign", "closed": "done"})
```

Run it first and verify the failure is the missing specified behavior, then implement against the interfaces above.

Tests are introduced incrementally: Task 1 covers only its delivered boundary;
add later-task assertions when that task begins. Capture red then green within
each task. Do not commit a deliberately failing suite or make future behavior
pass with placeholders. The first acceptance example may span multiple tasks;
add it at the task that owns its complete interface.

### Task 1: Paginated discovery

**Files:** src/ai_dlc/provider_onboarding.py, tests/test_provider_onboarding.py plus the directly affected source/generated files listed above.

**Consumes:** The specification, fixtures/examples described above, and completed dependency interfaces.

**Produces:** Implement discover_linear with injected httpx responses covering multiple teams, duplicate names, two started states, pagination, authorization failure, and incomplete result refusal. Expose no mutations or CLI apply in this task.

- [ ] 1.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 1.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 1.3 Implement discover_linear with injected httpx responses covering multiple teams, duplicate names, two started states, pagination, authorization failure, and incomplete result refusal. Expose no mutations or CLI apply in this task.
- [ ] 1.4 Run `uv run --locked --no-sync pytest -q tests/test_provider_onboarding.py tests/test_cli.py tests/test_rebind.py tests/test_providers.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 1.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 1.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 2: Selection and guarded local write

**Files:** src/ai_dlc/provider_onboarding.py, tests/test_provider_onboarding.py plus the directly affected source/generated files listed above.

**Consumes:** Task 1's committed artifacts and the shared interface contract above.

**Produces:** Implement plan_linear_connection and apply_linear_connection: validate selection membership/types and config digest, preserve comments and unrelated sections, write atomically, and prove invalid/stale selections write nothing. Task 3 owns CLI wiring and fresh remote membership checks.

- [ ] 2.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 2.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 2.3 Implement plan_linear_connection and apply_linear_connection: validate selection membership/types and config digest, preserve comments and unrelated sections, write atomically, and prove invalid/stale selections write nothing. Task 3 owns CLI wiring and fresh remote membership checks.
- [ ] 2.4 Run `uv run --locked --no-sync pytest -q tests/test_provider_onboarding.py tests/test_cli.py tests/test_rebind.py tests/test_providers.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 2.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 2.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 3: CLI and guarded apply

**Files:** src/ai_dlc/cli.py plus the directly affected source/generated files listed above.

**Consumes:** Task 2's committed artifacts and the shared interface contract above.

**Produces:** Implement provider connect preview/apply, credential-redacted errors, and binding-drift refusal. Add a sandbox read-only walkthrough procedure.

- [ ] 3.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 3.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 3.3 Implement provider connect preview/apply, credential-redacted errors, and binding-drift refusal. Add a sandbox read-only walkthrough procedure.
- [ ] 3.4 Run `uv run --locked --no-sync pytest -q tests/test_provider_onboarding.py tests/test_cli.py tests/test_rebind.py tests/test_providers.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 3.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 3.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

## Requirement coverage

| Requirement / verification criterion | Tasks | Verification |
| --- | --- | --- |
| LN-01: Complete scoped discovery | 1, 2 | Focused positive and refusal cases, then integration and required project checks. |
| LN-02: Validated local preview and apply | 1, 2, 3 | Focused positive and refusal cases, then integration and required project checks. |
| LN-03: Existing work and credentials stay stable | 2, 3 | Focused positive and refusal cases, then integration and required project checks. |

## Completion and handoff

- [ ] Run `ai-dlc project check --required`; inspect all five outcomes.
- [ ] Run `openspec validate linear-provider-onboarding --strict --no-interactive`, review against this plan, and archive only after all implementation tasks are complete. Update the work record to the exact archived path.
- [ ] Create/link the PR, complete review and required CI, and use `ai-dlc work finish linear-provider-onboarding` only after merge evidence exists.
- [ ] Leave a handoff with work/ticket ID, branch and revision, delivered interfaces, checks and evidence locations, unresolved findings, and the next dependency-unblocked ticket.

Stop and report a blocked task if a dependency is incomplete, an accepted interface conflicts with existing behavior, a required live environment is unavailable, or a required human label/budget is absent. Continue independent local preparation where possible. Do not invent missing product decisions or broaden scope to clear a blocker.
