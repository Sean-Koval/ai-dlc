# Import pinned workflow guidance and expose it to supported harnesses Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when delegation is authorized. Steps use checkbox syntax for tracking.

**Goal:** Make a replaceable workflow bundle reproducible in the project repository and discoverable to the harness using existing managed rendering.

**Architecture:** Use the exact format, import/activation separation, lock schema,
limits, destinations, collision rules, transactional behavior, readiness states,
and offline sequence frozen in the OpenSpec [design](../../../openspec/changes/portable-workflow-bundles/design.md).
Import accepts only portable Git transports, previews exact content metadata, and
vendors reviewed bytes without selecting or rendering. Project-only
`agents.bundles` is the separate activation decision. Rendering exposes skills in
the supported client-native directories, templates at `docs/templates/NAME.md`,
and both through the managed project guidance index. Existing `agents.skills`
continues to select shipped skills. Import and rendering never execute bundle
content; the separately activated guidance remains untrusted input to a harness.

**Tech Stack:** Python 3.12, existing AI-DLC CLI/services, Markdown workflow assets, OpenSpec, and configured tracker/SCM adapters. Reuse existing dependencies; any new dependency requires a documented necessity and explicit review.

**Spec:** [portable-workflow-bundles](../../../openspec/changes/portable-workflow-bundles/specs/portable-workflow-bundles/spec.md)

## Global constraints

No arbitrary installer/scripts, marketplace, dependency solver, new client adapter, remote auto-update, or changes to personal profile enrollment semantics.

Milestone: M1. Dependencies: `component-capability-contract`,
`connected-project-readiness`, `linear-provider-onboarding` (project write-lock
coordination only).

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

`validate_bundle(root: Path, manifest: dict) -> dict` returns a validated schema-1
manifest; the resolver's raw JSON loader rejects duplicate keys before this
dictionary boundary. `resolve_bundle(source: str, ref: str, bundle_id: str, *,
environ) -> BundleCandidate` does not activate files. `import_bundle(root: Path,
candidate, *, apply: bool = False, expected_commit: str | None = None) -> dict`
returns the exact deterministic result schema defined in the OpenSpec design;
apply requires the matching preview commit. `BundleCandidate` includes the
manifest digest as defined there. No active profile lock is mutated.

### Files and ownership

- Create src/ai_dlc/workflow_bundles.py
- Modify src/ai_dlc/profile_source.py
- Modify src/ai_dlc/agents.py
- Modify src/ai_dlc/cli.py
- Modify src/ai_dlc/config.py
- Modify src/ai_dlc/readiness.py
- Test tests/test_workflow_bundles.py
- Modify tests/test_profile_source.py, tests/test_rendering.py, tests/test_templates.py, tests/test_config.py, tests/test_readiness.py, tests/test_cli.py

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

**Produces:** Implement duplicate-key-safe manifest loading and `validate_bundle`
with malformed, oversized, traversal, symlink, non-regular, extra-file, digest,
duplicate name/path, exact export coverage, and portable skill-frontmatter cases
under the frozen limits. The requested-ID comparison belongs to Task 2's resolver
because `validate_bundle` intentionally receives no requested ID. Validate all
assets before planning a write; imports and rendering remain Tasks 2 and 3.

- [x] 1.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [x] 1.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [x] 1.3 Implement duplicate-key-safe manifest loading and `validate_bundle` with malformed, oversized, traversal, symlink, non-regular, extra-file, digest, duplicate name/path, exact export coverage, and portable skill-frontmatter cases under the frozen limits. Requested-ID comparison remains Task 2 resolver behavior. Validate all assets before planning a write; imports and rendering remain Tasks 2 and 3.
- [x] 1.4 Run `uv run --locked --no-sync pytest -q tests/test_workflow_bundles.py tests/test_profile_source.py tests/test_rendering.py tests/test_templates.py tests/test_config.py tests/test_readiness.py tests/test_cli.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [x] 1.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [x] 1.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 2: Pinned import preview/apply

**Files:** src/ai_dlc/workflow_bundles.py plus the directly affected source/generated files listed above.

**Consumes:** Task 1's committed artifacts and the shared interface contract above.

**Produces:** Implement portable temporary source resolution, requested/manifest
ID equality, reviewed revision matching at the service boundary, the exact
vendored lock, intact same-owner updates, and rollback on partial file errors.
Import must not select, render, or edit config. Preserve the existing
profile-source security contract when sharing helpers.

- [x] 2.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [x] 2.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [x] 2.3 Implement portable temporary source resolution, requested/manifest ID equality, reviewed revision matching at the service boundary, the specified complete vendored lock, intact same-owner update guards, and transactional rollback. Import must not select, render, or edit config. Preserve the existing profile-source security contract when sharing helpers.
- [x] 2.4 Run `uv run --locked --no-sync pytest -q tests/test_workflow_bundles.py tests/test_profile_source.py tests/test_rendering.py tests/test_templates.py tests/test_config.py tests/test_readiness.py tests/test_cli.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [x] 2.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [x] 2.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 3: Client and template distribution

**Files:** src/ai_dlc/agents.py plus the directly affected source/generated files listed above.

**Consumes:** Task 2's committed artifacts and the shared interface contract above.

**Produces:** Extend owned skill/template/index rendering, project-only config validation, and bundle-aware readiness. Demonstrate one external Markdown bundle in a fresh checkout with the source unavailable and every Git/network seam guarded against use.

- [ ] 3.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 3.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 3.3 Extend owned skill/template/index rendering, project-only config validation, and bundle-aware readiness. Demonstrate one external Markdown bundle in a fresh checkout with the source unavailable and every Git/network seam guarded against use.
- [ ] 3.4 Run `uv run --locked --no-sync pytest -q tests/test_workflow_bundles.py tests/test_profile_source.py tests/test_rendering.py tests/test_templates.py tests/test_config.py tests/test_readiness.py tests/test_cli.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 3.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 3.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

## Requirement coverage

| Requirement / verification criterion | Tasks | Verification |
| --- | --- | --- |
| WB-01: Pinned portable workflow assets | 1, 2 | Duplicate-safe parsing; path/type/limit/digest/source/ID refusals; exact preview; moved-ref refusal; complete deterministic lock; transactional vendoring. |
| WB-02: Owned rendering and integrity | 1, 2, 3 | Intact same-owner updates; local edit, authored target, shipped-name, cross-bundle, tamper, and publication-failure cases with unchanged-byte assertions. |
| WB-03: Direct use and offline continuation | 2, 3 | Project-only schema cases; generated index/client/template destinations; readiness states; fresh-checkout render/check with source and Git access disabled. |

## Completion and handoff

- [ ] Run `ai-dlc project check --required`; inspect all five outcomes.
- [ ] Run `openspec validate portable-workflow-bundles --strict --no-interactive`, review against this plan, and archive only after all implementation tasks are complete. Update the work record to the exact archived path.
- [ ] Create/link the PR, complete review and required CI, and use `ai-dlc work finish portable-workflow-bundles` only after merge evidence exists.
- [ ] Leave a handoff with work/ticket ID, branch and revision, delivered interfaces, checks and evidence locations, unresolved findings, and the next dependency-unblocked ticket.

Stop and report a blocked task if a dependency is incomplete, an accepted interface conflicts with existing behavior, a required live environment is unavailable, or a required human label/budget is absent. Continue independent local preparation where possible. Do not invent missing product decisions or broaden scope to clear a blocker.
