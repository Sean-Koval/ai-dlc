# Portable Tracker Adapters Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans after design and target-deployment review.

**Goal:** Run the existing AI-DLC lifecycle through GitHub Issues, Plane and Jira,
with provider differences expressed through capabilities.
**Architecture:** Small httpx adapters implement normalized contracts; common workflow consumes capabilities and retains journals/gates.
**Tech Stack:** Existing Python/httpx/Pydantic/provider conformance infrastructure.
**Spec:** [portable-tracker-adapters](../../../openspec/changes/portable-tracker-adapters/specs/portable-tracker-adapters/spec.md).

Status: draft. [Master constraints](2026-09-06-provider-toolsets.md) apply. Jira Cloud
is confirmed; Data Center remains outside scope. GitHub Issues is an existing
adapter to integrate and qualify, not a new implementation from scratch.

## Task 1: Declare tracker capabilities without provider-name dispatch

**Files:** `src/ai_dlc/contracts.py`, `providers/__init__.py`, `providers/linear.py`,
`providers/github_issues.py`, `workflow.py`, generated `contracts/`; tests in
`test_providers.py`, `test_workflow.py`; create `tests/test_tracker_capabilities.py`.
**Interface:** optional `capabilities` operation, empty payload; response
`{"schema": 1, "lifecycle": {"in_progress": bool, "closed": bool}, "optional_operations": list[str]}`.
Unknown support remains explicitly unverified rather than coerced to true/false.

- [ ] Add red service tests registering a synthetic provider under a new alias with no in-progress capability; assert no transition call and the existing started/unsupported result.
- [ ] Add legacy provider tests without the optional capability response; retain its prior transition behavior.
- [ ] Declare discovery support in registry definitions before invocation; test that opted-in authentication/network/schema failures do not fall through to legacy behavior.
- [ ] Implement capability dispatch, declare built-in behavior, and remove the GitHub-name branch from work start. Do not alter completion gate evaluation.
- [ ] Regenerate contract schemas and test terminal-transition protection, unknown capability versions, and duplicate correlations; commit after focused checks.

## Task 1a: GitHub Issues as the first existing-provider proof

**Files:** existing `providers/github_issues.py`, shared connection definitions,
component/provider guidance, and `tests/test_providers.py`; add focused adapter
and shared lifecycle cases where coverage is absent.

- [ ] Reuse the existing gh-backed implementation. Add repository/account discovery
  through common onboarding and verify the selected host/repository identity.
- [ ] Test publish/start/status/gated finish with GitHub Issues and provider aliases.
  Starting local work must report the unsupported remote in-progress transition;
  do not silently invent labels or require GitHub Projects.
- [ ] Test complete/ambiguous correlations, uncertain create recovery, issue origin,
  and remote completion reasons. Inspect native completion metadata before deciding
  normalization; do not assume every closed issue represents successful completion.
- [ ] Preserve existing binding fingerprints, including GitHub SCM configuration
  currently included in their identity; no incidental fingerprint migration.
  Verify changing tracker selection leaves SCM/PR/CI configuration unchanged.
- [ ] Qualify one disposable repository lifecycle and named-resource setup. Record
  fixture and live evidence separately; current gh wrapper tests are not live proof.

## Task 2: Plane vertical slice

**Files:** create `src/ai_dlc/providers/plane.py`, `tests/test_plane_provider.py`;
register in provider definitions/registry; add `agents/providers/plane.md`, component
metadata and reviewed native connector/module setup; update conformance targets.
**Interface:** `PlaneProvider(config, *, client=None, environ=None).invoke(operation, payload) -> dict` uses existing tracker payloads and capability response.

- [ ] Resolve supported deployed Plane edition/version and inspect current API schema. Prove the correlation field survives create/read/search before committing to its representation.
- [ ] Add request/response fixture tests using httpx MockTransport, including complete pagination and native state mapping. Hand-author expected state/URL/IDs:

```python
def test_plane_reports_completed_as_closed(plane_provider):
    item = plane_provider.invoke("read", {"reference": "reviewed-item"})
    assert item["state"] == "closed"
    assert item["id"] == "reviewed-item"
```

- [ ] Verify red; implement create/find/read/transition/link plus scoped origin/authentication. Preserve native state metadata and fail on incomplete reconciliation.
- [ ] Test accepted-but-timed-out create, duplicate markers, wrong project, deleted item, rate limit, unavailable field, cancellation and credential redaction.
- [ ] Add discovery of names/states through the common connection API; configure native MCP separately. Run unchanged WorkService lifecycle tests with this adapter and commit.
- [ ] In an explicitly disposable live project, prove duplicate-safe publish/start/status and gated finish, recording actual evidence. Read-only health is not this gate.

## Task 3: Jira as the second portability proof

**Files:** create `src/ai_dlc/providers/jira.py`, `tests/test_jira_provider.py`;
extend provider definitions, component/guidance and conformance metadata.
**Interface:** `JiraProvider(config, *, client=None, environ=None).invoke(operation, payload) -> dict`, same lifecycle interface as Plane.

- [ ] Verify work deployment and permitted authentication. Discover project, issue type, create fields, transition fields and available transitions; record limitations before coding.
- [ ] Add red fixtures for ADF body conversion, correlation round-trip, ambiguous transitions, required fields, complete project-scoped reconciliation and normalized cancellation.
- [ ] Implement adapter requests and discovery only. If another Jira-name branch seems necessary in WorkService, revise the capability contract before proceeding.
- [ ] Run the shared lifecycle suite and native connection smoke check; then a disposable live cycle using real transition policies.
- [ ] Run required manifest checks, strict spec validation and independent review. Archive/finish this child only when its complete stated scope is delivered; report pending live gates honestly.

Coverage: Task 1 TA-02; Tasks 1a–3 TA-01/TA-03/TA-04/TA-05; Task 1a TA-06.
