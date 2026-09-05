# Connect provider roles to tool installation and harness guidance Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when delegation is authorized. Steps use checkbox syntax for tracking.

**Goal:** Resolve explicitly selected provider roles into a deterministic, versioned description of required tools, guidance, configuration, and checks.

**Architecture:** Component schema 1 contains id, roles, modules, guidance, required_config. Modules name existing entries in modules/catalog.toml; guidance is a list of repository/package-relative Markdown paths. Built-ins are indexed by provider kind. An optional providers.<id>.component overrides the component ID. Optional providers.<id>.component_manifest and component_manifest_sha256 select a checked-in JSON manifest verified before parsing. Unknown fields, duplicate IDs, unsafe paths, missing hashes, unknown modules, and incompatible roles fail validation. No manifest command strings or installers are executed. Native adapters remain in the existing provider registry.

**Tech Stack:** Python 3.12, existing AI-DLC CLI/services, Markdown workflow assets, OpenSpec, and configured tracker/SCM adapters. Reuse existing dependencies; any new dependency requires a documented necessity and explicit review.

**Spec:** [component-capability-contract](../../../openspec/changes/component-capability-contract/specs/component-capability-contract/spec.md)

## Global constraints

No package registry, remote downloads, new provider operations, model selection, or changes to finish gates.

Milestone: M1. Dependencies: none; ready after the planning branch is integrated.

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

resolve_components(config: dict, catalog: dict) -> dict returns {schema: 1, components: [{id, provider, role, modules, guidance, required_config}], unresolved: [{provider, role, reason}]}. Lists are sorted by stable IDs. This function is pure and accepts only explicitly selected roles; the caller excludes compatibility-only base defaults.

### Files and ownership

- Create src/ai_dlc/components.py
- Create modules/components.json
- Create agents/providers/openspec.md, agents/providers/linear.md, agents/providers/github-issues.md
- Test packaged assets in tests/test_templates.py
- Modify src/ai_dlc/config.py
- Test tests/test_components.py
- Modify tests/test_config.py

All listed source/test paths are relative to the repository root. New paths are proposed deliverables, not claims that those files exist today.

## First executable acceptance example

The following is a target regression, to be added during implementation. It is not run in this documentation change.

```python
from ai_dlc.components import resolve_components

def test_selected_spec_requires_its_tool():
    catalog = {"schema": 1, "components": [{"id": "openspec", "roles": ["specs"], "modules": ["openspec"], "guidance": ["guidance/openspec.md"], "required_config": []}]}
    result = resolve_components({"roles": {"specs": "openspec"}}, catalog)
    assert result["components"][0]["modules"] == ["openspec"]
    assert result["unresolved"] == []
```

Run it first and verify the failure is the missing specified behavior, then implement against the interfaces above.

Tests are introduced incrementally: Task 1 covers only its delivered boundary;
add later-task assertions when that task begins. Capture red then green within
each task. Do not commit a deliberately failing suite or make future behavior
pass with placeholders. The first acceptance example may span multiple tasks;
add it at the task that owns its complete interface.

### Task 1: Validated component catalog

**Files:** src/ai_dlc/components.py, modules/components.json, agents/providers/*.md, tests/test_components.py plus the directly affected source/generated files listed above.

**Consumes:** The specification, fixtures/examples described above, and completed dependency interfaces.

**Produces:** Implement catalog loading/validation with schema-1 fixtures for openspec, linear, github-issues and two synthetic providers. Reject missing modules, duplicate IDs, digest mismatches and unsafe paths; ship referenced built-in guidance. Keep role resolution for Task 2 and provider configuration integration for Task 3.

- [ ] 1.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 1.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 1.3 Implement catalog loading/validation with schema-1 fixtures for openspec, linear, github-issues and two synthetic providers. Reject missing modules, duplicate IDs, digest mismatches and unsafe paths; ship referenced built-in guidance. Keep role resolution for Task 2 and provider configuration integration for Task 3.
- [ ] 1.4 Run `uv run --locked --no-sync pytest -q tests/test_components.py tests/test_config.py tests/test_providers.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 1.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 1.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 2: Pure resolution

**Files:** src/ai_dlc/components.py plus the directly affected source/generated files listed above.

**Consumes:** Task 1's committed artifacts and the shared interface contract above.

**Produces:** Implement catalog validation and resolve_components; keep installation, network, writes, and provider operations outside the resolver. Preserve unresolved-provider diagnostics.

- [ ] 2.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 2.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 2.3 Implement catalog validation and resolve_components; keep installation, network, writes, and provider operations outside the resolver. Preserve unresolved-provider diagnostics.
- [ ] 2.4 Run `uv run --locked --no-sync pytest -q tests/test_components.py tests/test_config.py tests/test_providers.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 2.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 2.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 3: Configuration integration

**Files:** src/ai_dlc/config.py plus the directly affected source/generated files listed above.

**Consumes:** Task 2's committed artifacts and the shared interface contract above.

**Produces:** Validate the three optional provider metadata fields and machine-layer refusal; document a complete third-party manifest example and verify packaged component data.

- [ ] 3.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 3.2 Add focused failing cases for this task's specified behavior and failure paths. Run the named focused suite and capture the expected failure before implementation.
- [ ] 3.3 Validate the three optional provider metadata fields and machine-layer refusal; document a complete third-party manifest example and verify packaged component data.
- [ ] 3.4 Run `uv run --locked --no-sync pytest -q tests/test_components.py tests/test_config.py tests/test_providers.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 3.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 3.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

## Requirement coverage

| Requirement / verification criterion | Tasks | Verification |
| --- | --- | --- |
| CC-01: Deterministic capability resolution | 1, 2 | Focused positive and refusal cases, then integration and required project checks. |
| CC-02: Verified extension metadata | 1, 2, 3 | Focused positive and refusal cases, then integration and required project checks. |
| CC-03: Compatibility and provenance | 2, 3 | Focused positive and refusal cases, then integration and required project checks. |

## Completion and handoff

- [ ] Run `ai-dlc project check --required`; inspect all five outcomes.
- [ ] Run `openspec validate component-capability-contract --strict --no-interactive`, review against this plan, and archive only after all implementation tasks are complete. Update the work record to the exact archived path.
- [ ] Create/link the PR, complete review and required CI, and use `ai-dlc work finish component-capability-contract` only after merge evidence exists.
- [ ] Leave a handoff with work/ticket ID, branch and revision, delivered interfaces, checks and evidence locations, unresolved findings, and the next dependency-unblocked ticket.

Stop and report a blocked task if a dependency is incomplete, an accepted interface conflicts with existing behavior, a required live environment is unavailable, or a required human label/budget is absent. Continue independent local preparation where possible. Do not invent missing product decisions or broaden scope to clear a blocker.
