# Import pinned workflow guidance and expose it to supported harnesses Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when delegation is authorized. Steps use checkbox syntax for tracking.

**Goal:** Make a replaceable workflow bundle reproducible in the project repository and discoverable to the harness using existing managed rendering.

**Architecture:** First bundle format is schema=1, id, skills mapping names to relative SKILL.md paths, templates mapping names to relative Markdown paths, and files mapping every included relative path to sha256. First delivery allows regular UTF-8 Markdown only, at most 2 MiB/file and 10 MiB total; no symlinks, scripts, absolute paths, traversal, or undeclared files. Guidance remains untrusted input for the receiving harness. Add ai-dlc agents bundle import SOURCE --ref REF --id ID [--apply --expected-commit SHA]; preview can fetch to temporary storage but cannot change active files. Reuse existing Git source validation through a public shared helper while preserving profile-source tests; resolve an advertised ref to an exact commit and compare it again on apply. Apply vendors selected files plus a lock under .ai-dlc/bundles/ID. Project-only agents.bundles selects these IDs, so Git transports them between machines. Existing agents.skills remains shipped-skill selection. Resolve name collisions by refusing, never overwrite. No remote registry or automatic startup fetch. The --expected-commit flag is required for apply and must equal the previewed commit. Import operates on a bundle root containing bundle.json and its declared payload; Git metadata is excluded. References in Markdown never authorize execution. Add agents.bundles to project-only nested configuration validation; reject it in personal/machine layers in this first delivery.

**Tech Stack:** Python 3.12, existing AI-DLC CLI/services, Markdown workflow assets, OpenSpec, and configured tracker/SCM adapters. Reuse existing dependencies; any new dependency requires a documented necessity and explicit review.

**Spec:** [portable-workflow-bundles](../../../openspec/changes/portable-workflow-bundles/specs/portable-workflow-bundles/spec.md)

## Global constraints

No arbitrary installer/scripts, marketplace, dependency solver, new client adapter, remote auto-update, or changes to personal profile enrollment semantics.

Milestone: M1. Dependencies: `component-capability-contract`, `connected-project-readiness`.

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

validate_bundle(root: Path, manifest: dict) -> dict returns a validated schema-1 manifest. resolve_bundle(source:str, ref:str, bundle_id:str, *, environ) -> candidate with resolved_commit and file hashes; it does not activate files. import_bundle(root:Path, candidate, *, apply:bool=False) -> {applied, changed, conflicts, resolved_commit}. The candidate type and cleanup lifecycle are defined in workflow_bundles.py; no active profile lock is mutated.

### Files and ownership

- Create src/ai_dlc/workflow_bundles.py
- Modify src/ai_dlc/agents.py
- Modify src/ai_dlc/cli.py
- Modify src/ai_dlc/config.py
- Test tests/test_workflow_bundles.py
- Modify tests/test_rendering.py, tests/test_templates.py

All listed source/test paths are relative to the repository root. New paths are proposed deliverables, not claims that those files exist today.

## First executable acceptance example

The following is a target regression, to be added during implementation. It is not run in this documentation change.

```python
import pytest
from ai_dlc.workflow_bundles import validate_bundle

def test_bundle_rejects_path_escape(tmp_path):
    manifest = {"schema": 1, "id": "example", "skills": {"example": "../SKILL.md"}, "templates": {}, "files": {"../SKILL.md": "0" * 64}}
    with pytest.raises(ValueError):
        validate_bundle(tmp_path, manifest)
```

Run it first and verify the failure is the missing specified behavior, then implement against the interfaces above.

Tests are introduced incrementally: Task 1 covers only its delivered boundary;
add later-task assertions when that task begins. Capture red then green within
each task. Do not commit a deliberately failing suite or make future behavior
pass with placeholders. The first acceptance example may span multiple tasks;
add it at the task that owns its complete interface.

### Task 1: Manifest and digest validation

**Files:** tests/test_workflow_bundles.py plus the directly affected source/generated files listed above.

**Consumes:** The specification, fixtures/examples described above, and completed dependency interfaces.

**Produces:** Implement validate_bundle with malformed, oversized, traversal, symlink, extra-file, digest mismatch, and duplicate-name cases. Validate all assets before planning a write; imports and rendering remain Tasks 2 and 3.

- [ ] 1.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 1.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 1.3 Implement validate_bundle with malformed, oversized, traversal, symlink, extra-file, digest mismatch, and duplicate-name cases. Validate all assets before planning a write; imports and rendering remain Tasks 2 and 3.
- [ ] 1.4 Run `uv run --locked --no-sync pytest -q tests/test_workflow_bundles.py tests/test_profile_source.py tests/test_rendering.py tests/test_templates.py tests/test_config.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 1.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 1.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 2: Pinned import preview/apply

**Files:** src/ai_dlc/workflow_bundles.py plus the directly affected source/generated files listed above.

**Consumes:** Task 1's committed artifacts and the shared interface contract above.

**Produces:** Implement temporary source resolution, reviewed revision matching, vendored lock, and rollback on partial file errors. Preserve the existing profile-source security contract when sharing helpers.

- [ ] 2.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 2.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 2.3 Implement temporary source resolution, reviewed revision matching, vendored lock, and rollback on partial file errors. Preserve the existing profile-source security contract when sharing helpers.
- [ ] 2.4 Run `uv run --locked --no-sync pytest -q tests/test_workflow_bundles.py tests/test_profile_source.py tests/test_rendering.py tests/test_templates.py tests/test_config.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 2.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 2.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 3: Client and template distribution

**Files:** src/ai_dlc/agents.py plus the directly affected source/generated files listed above.

**Consumes:** Task 2's committed artifacts and the shared interface contract above.

**Produces:** Extend owned skill/template rendering and project-only config validation; demonstrate one external Markdown bundle in a fresh checkout, offline.

- [ ] 3.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 3.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 3.3 Extend owned skill/template rendering and project-only config validation; demonstrate one external Markdown bundle in a fresh checkout, offline.
- [ ] 3.4 Run `uv run --locked --no-sync pytest -q tests/test_workflow_bundles.py tests/test_profile_source.py tests/test_rendering.py tests/test_templates.py tests/test_config.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 3.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 3.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

## Requirement coverage

| Requirement / verification criterion | Tasks | Verification |
| --- | --- | --- |
| WB-01: Pinned portable workflow assets | 1, 2 | Focused positive and refusal cases, then integration and required project checks. |
| WB-02: Owned rendering and integrity | 1, 2, 3 | Focused positive and refusal cases, then integration and required project checks. |
| WB-03: Direct use and offline continuation | 2, 3 | Focused positive and refusal cases, then integration and required project checks. |

## Completion and handoff

- [ ] Run `ai-dlc project check --required`; inspect all five outcomes.
- [ ] Run `openspec validate portable-workflow-bundles --strict --no-interactive`, review against this plan, and archive only after all implementation tasks are complete. Update the work record to the exact archived path.
- [ ] Create/link the PR, complete review and required CI, and use `ai-dlc work finish portable-workflow-bundles` only after merge evidence exists.
- [ ] Leave a handoff with work/ticket ID, branch and revision, delivered interfaces, checks and evidence locations, unresolved findings, and the next dependency-unblocked ticket.

Stop and report a blocked task if a dependency is incomplete, an accepted interface conflicts with existing behavior, a required live environment is unavailable, or a required human label/budget is absent. Continue independent local preparation where possible. Do not invent missing product decisions or broaden scope to clear a blocker.
