# Qualify portable setup, provider replacement, and development handoffs Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only when delegation is authorized. Steps use checkbox syntax for tracking.

**Goal:** Produce reproducible evidence that the delivered framework works on the initial supported environments and supports one safe provider substitution.

**Architecture:** Initial live qualification targets are a clean native macOS arm64 environment and clean Ubuntu 24.04 arm64 devcontainer; hosted clients and new harness adapters remain separate unqualified targets. If a target is inaccessible, record unavailable and leave the corresponding acceptance unmet. Use a disposable project and separately scoped credentials. Demonstrate provider-neutral tracker behavior using Linear and the already implemented GitHub Issues adapter on designated sandbox destinations, including absence of in_progress on GitHub Issues. Never change this project's tracker to perform the experiment. Test same-revision repeat setup, offline guidance, authored-file preservation, resumed work, and a staged update failure. All live writes require explicit disposable destinations in the run configuration.

**Tech Stack:** Python 3.12, existing AI-DLC CLI/services, Markdown workflow assets, OpenSpec, and configured tracker/SCM adapters. Reuse existing dependencies; any new dependency requires a documented necessity and explicit review.

**Spec:** No new formal behavior: this ticket verifies its predecessor contracts.

## Global constraints

No production tracker changes, invented clean-machine evidence, new platform support, package publication, or automatic closure when an environment is unavailable.

Milestone: M3. Dependencies: `connected-project-readiness`, `linear-provider-onboarding`, `portable-workflow-bundles`, `spec-delivery-traceability`.

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

Report fields: commit, profile_revision, bundle_revisions, environment, harness_version, scenario_id, steps, expected, observed, evidence, result, limitations. result is passed/failed/unavailable/not-run. Evidence is fixture, live-local, live-container, or live-hosted and is never promoted between categories.

### Files and ownership

- Create docs/verification/framework-qualification.md
- Create scripts/qualify_framework.py
- Create tests/test_qualification_report.py
- Update docs/release-verification.md

All listed source/test paths are relative to the repository root. New paths are proposed deliverables, not claims that those files exist today.

## Behavioral review cases

For each criterion below, preserve the input, produced artifact or observation, expected result, actual result, and evidence. Packaging checks only prove asset delivery; they do not substitute for these cases.

- **Q-01 — Setup continuity:** Demonstrate equivalent portable requirements on both initial targets with independent local bindings and a repeat setup that creates no duplicate owned assets.
- **Q-02 — Provider substitution:** Demonstrate a new work cycle using each tracker adapter without changing workflow rationale; existing records stay bound, and unsupported transitions are explicit.
- **Q-03 — Handoff and honest evidence:** A fresh session completes the next action from project artifacts alone; report tool/client limits and preserve transcripts and receipts for each actual target.

### Task 1: Prepare repeatable protocol

**Files:** scripts/qualify_framework.py plus the directly affected source/generated files listed above.

**Consumes:** The specification, fixtures/examples described above, and completed dependency interfaces.

**Produces:** Write exact environment bootstrap commands, disposable source/target checks, result schema, evidence paths, and cleanup instructions; validate report classification without live writes.

- [ ] 1.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 1.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 1.3 Write exact environment bootstrap commands, disposable source/target checks, result schema, evidence paths, and cleanup instructions; validate report classification without live writes.
- [ ] 1.4 Run `uv run --locked --no-sync pytest -q tests/test_qualification_report.py tests/test_machine_integration.py tests/test_rebind.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 1.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 1.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 2: Run supported target walkthroughs

**Files:** docs/verification/framework-qualification.md plus the directly affected source/generated files listed above.

**Consumes:** Task 1's committed artifacts and the shared interface contract above.

**Produces:** Execute the same scenario from clean native and container environments, repeat setup, simulate restart and unavailable source, and retain evidence per target.

- [ ] 2.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 2.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 2.3 Execute the same scenario from clean native and container environments, repeat setup, simulate restart and unavailable source, and retain evidence per target.
- [ ] 2.4 Run `uv run --locked --no-sync pytest -q tests/test_qualification_report.py tests/test_machine_integration.py tests/test_rebind.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 2.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 2.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

### Task 3: Prove replacement and handoff

**Files:** docs/release-verification.md plus the directly affected source/generated files listed above.

**Consumes:** Task 2's committed artifacts and the shared interface contract above.

**Produces:** Use two scoped sandbox tracker destinations and a fresh-session handoff; record actual behavior, gate failures, unsupported transitions, and remaining release gaps.

- [ ] 3.1 Inspect the named source and existing regression patterns; identify the exact requirement IDs covered by this task in the coverage table below.
- [ ] 3.2 Prepare the concrete cases and expected observations above before authoring or executing the workflow; mark human/live-only observations pending.
- [ ] 3.3 Use two scoped sandbox tracker destinations and a fresh-session handoff; record actual behavior, gate failures, unsupported transitions, and remaining release gaps.
- [ ] 3.4 Run `uv run --locked --no-sync pytest -q tests/test_qualification_report.py tests/test_machine_integration.py tests/test_rebind.py` after the listed new tests exist. Expected: all focused tests pass; investigate rather than skip failures.
- [ ] 3.5 Review the result against each mapped requirement, including excluded scope and compatibility; update the OpenSpec task checkboxes only for delivered behavior.
- [ ] 3.6 Commit only this task's related files with a conventional prefix and an outcome-focused message; carry exact commit/evidence into the handoff.

## Requirement coverage

| Requirement / verification criterion | Tasks | Verification |
| --- | --- | --- |
| Q-01: Setup continuity | 1, 2 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| Q-02: Provider substitution | 1, 2, 3 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |
| Q-03: Handoff and honest evidence | 2, 3 | Recorded behavioral case and evidence; unresolved human/live results remain pending. |

## Completion and handoff

- [ ] Run `ai-dlc project check --required`; inspect all five outcomes.
- [ ] Create/link the PR, complete review and required CI, and use `ai-dlc work finish framework-qualification` only after merge evidence exists.
- [ ] Leave a handoff with work/ticket ID, branch and revision, delivered interfaces, checks and evidence locations, unresolved findings, and the next dependency-unblocked ticket.

Stop and report a blocked task if a dependency is incomplete, an accepted interface conflicts with existing behavior, a required live environment is unavailable, or a required human label/budget is absent. Continue independent local preparation where possible. Do not invent missing product decisions or broaden scope to clear a blocker.
