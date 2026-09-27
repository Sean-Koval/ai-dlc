## 1. Project policy and compatibility

- [x] 1.1 Add configuration cases for omitted/default policy, both supported values, invalid types/values and personal/machine/team-source attempts to supply the field; inspect `src/ai_dlc/config.py` and existing configuration tests.
- [x] 1.2 Implement project-only `agents.bound_push_policy` validation and default all-branches semantics without enabling hooks or changing client capability fixtures.

## 2. Offline branch classification

- [x] 2.1 Add temporary-repository hook cases for a valid bound branch, multiple valid matching records, one invalid match among valid records, unreviewed/missing-tracker/provider-drifted records, unreadable inventory, detached identity and a truly unbound branch in both modes.
- [x] 2.2 Update `src/ai_dlc/harness/hooks.py` using existing offline work validation; require every matching record to be valid, reviewed and tracker-bound, and allow a truly unbound branch only in explicit tracked-branches mode.
- [x] 2.3 Verify no provider calls/journals or synthetic work records are created; retain existing destructive denials, ordinary payload results and unsupported-payload coverage.

## 3. Guidance, evidence and delivery

- [x] 3.1 Update applicable generated guidance/config examples and canonical small-change instructions to state the selected policy; verify no-hook configurations acquire no new record requirement.
- [x] 3.2 Run the real hook service against isolated Git fixtures, label native fixture coverage honestly and record the strict/default multi-record regression result.
- [x] 3.3 Complete specification/work-record and affected-document review, record required content-bound dispositions, strictly validate this change, run focused implementation checks, and resolve actionable review findings.

## Subsequent delivery gates

After implementation and the checklist above are complete, archive this independently owned change on its bound delivery branch with `ai-dlc work archive`. Repair moved artifact links and any evidence targets actually made stale by archival. Immediately before authorized merge, update from the target branch and refresh required checks/evidence. Finish through `ai-dlc work finish` against the exact merged revision and its configured receipts. These remain mandatory later delivery gates, not checkboxes that must falsely claim post-merge completion before archive. No package publication or paid comparison is authorized by this task list.


# Proportionate Push Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add an explicit project-owned `tracked-branches` mode to the optional `bound-push` hook while preserving strict omission behavior and every existing tracked-work validation boundary.

**Architecture:** Keep the policy as one validated scalar in existing configuration. Route only already-classified nondestructive bound operations through one offline helper in `harness/hooks.py`; it resolves the current branch and runtime configuration, establishes association from every local work record, and reuses `resolve_work` plus `validate_work` for every match. Generated guidance reads the effective per-client hook selection after team-source merging.

**Tech Stack:** Python 3.12, pytest, Pydantic/TOML configuration, existing Git runner and work-validation helpers.

**Spec:** `openspec/changes/proportionate-push-policy/specs/native-work-harnesses/spec.md` (PPP-01 through PPP-04), with `design.md` and `tasks.md` in the same change.

## Global Constraints

- Do not begin implementation until issue #176 is merged and the delivery branch is created from refreshed `main`; then re-read `docs/development-workflow.md` and the `repo-development-workflow` entry in `docs/catalog.toml`.
- Omission means `all-branches`; do not materialize that default into resolved config or change schema 4.
- Only the project layer may set `agents.bound_push_policy`; accepted values are exactly `all-branches` and `tracked-branches`.
- The policy does not select a hook, add payload/client coverage, query providers, create journals or work records, or weaken destructive-command denial and finish gates.
- Do not modify `agents/capabilities.toml`, work-record schema, `providers/scm.py`, receipt contracts, or provider/journal mutation services.

## Review Focus

- A malformed or non-regular `.ai-dlc/work/*.toml` entry must deny lightweight publication when branch association cannot be established; cover with an unreadable `.toml` directory and a malformed `artifacts.branch` value.
- More than one record may bind the branch; validate all matches and deny if any one is invalid, unreviewed, trackerless or binding-drifted.
- Detached HEAD or failed branch discovery must deny before an unbound exemption is possible.
- A team source may select `bound-push` but cannot carry policy; its exact `features` grammar must reject an added `bound_push_policy` key.
- Partial client rendering must advertise enforcement only when a client in that render's resolved `clients` list requires `bound-push`, including hooks merged from a validated team source.

---

## File map and ownership

- `src/ai_dlc/config.py`: owns scalar shape/value/layer validation only; no default insertion.
- `src/ai_dlc/harness/hooks.py`: owns branch/inventory classification and the native hook allow/deny response; imports only offline config, filesystem/Git and work-validation helpers.
- `src/ai_dlc/harness/agents.py`: owns conditional policy prose after team-source hooks have been merged and required-hook support validated.
- `tests/test_config.py`, `tests/test_hooks.py`, `tests/test_rendering.py`, `tests/test_team_sources.py`: observable regression coverage at their existing boundaries.
- `docs/development-workflow.md`, `docs/workflows/tool-map.md`, `docs/runbooks/machine-enrollment.md`: canonical workflow, interface and ownership explanations. `docs/catalog.toml` maps those claims to code, tests and the canonical native-work-harness requirement.
- `openspec/changes/proportionate-push-policy/{tasks.md,delivery.md}` and normal documentation evidence: completion bookkeeping after implementation; no new verification report.

### Task 1: Project-only configuration contract

**Files:**
- Modify: `src/ai_dlc/config.py` in `_validate`
- Test: `tests/test_config.py`
- Test: `tests/test_team_sources.py`

**Interfaces:**
- Consumes: existing `resolve_layers(layers: list[tuple[str, dict[str, Any]]]) -> Resolved` and native team-source `hooks/hooks.toml` grammar.
- Produces: optional `config["agents"]["bound_push_policy"]: Literal["all-branches", "tracked-branches"]`; consumers use `config.get("agents", {}).get("bound_push_policy", "all-branches")`.

- [x] Add failing `tests/test_config.py` cases proving omission leaves the key absent, both project values round-trip, non-string input raises `TypeError`, unsupported strings raise `ValueError`, and base/personal layers raise `cannot set agents.bound_push_policy`. Retain the existing top-level machine rejection (`machine: cannot set agents`) rather than widening `SCOPES`.
- [x] Add a failing `tests/test_team_sources.py` case using `source_setup` whose native `hooks/hooks.toml` contains both `features=["bound-push"]` and `bound_push_policy="tracked-branches"`; assert enrollment rejects the existing exact-document grammar. Keep/extend the normal named-hook case to prove `bound-push` selection itself remains accepted.
- [x] In `_validate`, add one `agents` field check: reject non-project ownership first, then require a string in the exact two-value set. Do not add an enum, schema revision, resolved default or new source schema.
- [x] Run `uv run --locked --no-sync pytest -q tests/test_config.py tests/test_team_sources.py` and require PASS.
- [x] Commit as `feat(config): add project push policy`.

### Task 2: Offline bound-operation decision

**Files:**
- Modify: `src/ai_dlc/harness/hooks.py`
- Test: `tests/test_hooks.py`

**Interfaces:**
- Consumes: `resolve_runtime(root).values`, `run_git(root, "branch", "--show-current", check=False)`, `inside(root, relative)`, `resolve_work(raw, config, work_id)`, and `validate_work(root, config, work_id)`.
- Produces: private `_bound_operation_decision(root: Path) -> dict[str, str]`, returning the existing native hook response shape. `_handle_hook` returns it only when `classify_command(...) == "bound-operation"`.

- [x] Replace the two minimal tests in `tests/test_hooks.py` with reusable local fixtures, without creating a shared test framework:
  - `initialize_hook_project(root: Path, policy: str | None) -> str` creates a real Git repository on branch `topic` and writes schema-4 project config.
  - `write_work_record(root: Path, work_id: str, **changes) -> Path` writes a complete schema-1 record with branch `topic`, `reviewed=true` and tracker `177` by default.
  - `hook_payload(command: str) -> dict` supplies the existing Bash payload.
- [x] Add failing parameterized service tests through public `handle_hook` for both `git push` and `gh pr create`: omitted/`all-branches` unbound denies with an `all-branches` remedy; explicit `tracked-branches` unbound allows with `coverage == "bound-operation"` and a policy-specific reason.
- [x] Add failing tests under both modes for one valid match and two valid matches (allow), then valid plus invalid match (deny and name the invalid ID). Parameterize invalid matches for `reviewed=false`, missing/blank tracker, parseable matching record missing a required schema field, and provider-binding drift. Build the drift fixture with the real `resolve_runtime`/`resolve_work` digest, then change the configured provider identity.
- [x] Add failing fail-closed tests for an invalid project policy, detached HEAD, a `.toml` directory that cannot be read, and `artifacts.branch` present with a non-string or blank value. Add a symlink/non-regular inventory case if `inside` does not already make the unreadable fixture cover it on the execution platform.
- [x] Extend the existing force-push test with explicit `tracked-branches` and no records; assert the unchanged destructive denial occurs before policy evaluation. Preserve existing ordinary and unsupported-payload assertions.
- [x] In all allow/deny fixtures snapshot work-record bytes before/after, assert no record was added, assert no `operations.sqlite3` exists anywhere below the fixture root/state, and monkeypatch `ai_dlc.work.workflow.Registry` to fail if instantiated. Omit `session_id` so the unrelated friction counter does not create fixture state.
- [x] Implement `_bound_operation_decision` as one bounded helper:
  1. Resolve a nonempty current branch and runtime config; convert Git/config/read failures into specific deny responses.
  2. Read the effective policy with strict fallback.
  3. Bind `.ai-dlc/work` and each sorted `*.toml` path through `inside`; TOML/read failures, non-table `artifacts`, or an `artifacts.branch` value that is present but not a nonblank string make inventory indeterminate and deny.
  4. Treat an absent branch key as a determinable nonmatch. Collect every exact branch match before validation.
  5. For every match, call `resolve_work` to obtain normalized review/artifact/binding state and `validate_work` to check filename/schema/local artifacts/dependency graph. Accumulate failures rather than accepting after the first valid record. Require `reviewed is True` and a nonblank tracker string.
  6. Deny accumulated tracked failures; allow valid matches in either policy; for no matches deny under `all-branches` and allow only under explicit `tracked-branches`.
- [x] Keep `classify_command` and its destructive/unsupported ordering byte-for-byte unless a failing regression proves a required change.
- [x] Run `uv run --locked --no-sync pytest -q tests/test_hooks.py` and require PASS.
- [x] Commit as `feat(hooks): allow proven unbound lightweight pushes`.

### Task 3: Capability-scoped generated guidance

**Files:**
- Modify: `src/ai_dlc/harness/agents.py`
- Test: `tests/test_rendering.py`
- Test: `tests/test_team_sources.py`

**Interfaces:**
- Consumes: effective `config["agents"]["clients"][client]["required_hooks"]` after `merge_source_items(...)` and the resolved render `clients: list[str]`.
- Produces: `_shared_guidance_lines(config: dict[str, Any], clients: list[str], index: str, bundle_index: str) -> list[str]` (update its sole call site in `_render_agents`).

- [x] Add failing rendering tests for a supported client requiring `bound-push`: omitted policy produces strict wording that covered publication still needs reviewed tracker-bound work even when the general workflow permits a record-free PR; `tracked-branches` produces proven-unbound wording and preserves complete validation for associated work.
- [x] Add a policy-without-hook case asserting no `bound-push`, `all-branches` or `tracked-branches` enforcement prose appears. Keep `test_unsupported_required_hooks_fail_before_writes` passing unchanged.
- [x] Extend the native team-source named-hook fixture to select `bound-push` for a supported client and assert the effective policy prose appears, proving guidance observes the already-validated merged hook instead of reparsing source content.
- [x] Pass `clients` into `_shared_guidance_lines`. Compute `uses_bound_push` only from those clients' effective `required_hooks`; when true append one mode-specific paragraph and one common limits paragraph. The common paragraph must state supported payload coverage and keep remote tracker state, arbitrary terminal enforcement, native approval/review, required checks, merge identity, receipts and finish separate.
- [x] Run `uv run --locked --no-sync pytest -q tests/test_rendering.py tests/test_team_sources.py` and require PASS.
- [x] Commit as `feat(agents): render selected push policy guidance`.

### Task 4: Canonical docs, mappings and delivery gates

**Files:**
- Modify: `docs/development-workflow.md`
- Modify: `docs/workflows/tool-map.md`
- Modify: `docs/runbooks/machine-enrollment.md`
- Modify: `docs/catalog.toml`
- Modify: `openspec/changes/proportionate-push-policy/tasks.md`
- Modify only if evidence fields need final results: `openspec/changes/proportionate-push-policy/delivery.md`

**Interfaces:**
- Consumes: final response wording and post-#176 canonical text.
- Produces: one consistent explanation plus catalog mappings to `config.py`, `hooks.py`, `agents.py`, the four focused tests and `openspec/specs/native-work-harnesses/spec.md` after archive promotion.

- [x] Re-read the #176-merged “When a work record is needed” section and add the optional-hook qualification: strict mode still requires a record for covered publication; explicit `tracked-branches` permits only proven-unbound covered nondestructive push/PR-create, while associated records remain fully validated.
- [x] Expand the Agent configuration row/nearby explanation in `tool-map.md` with the two modes and payload/completion limits. In `machine-enrollment.md`, state that team sources may select an existing hook feature but shared project config alone owns `bound_push_policy`.
- [x] Update existing catalog entries rather than adding a document: extend `repo-development-workflow` and `workflow-tool-map` with the three implementation files, focused tests and native-work-harness requirement; add `tests/test_config.py` and `tests/test_hooks.py` to `repo-runbooks-machine-enrollment` verification if absent. Preserve all mappings merged by #176.
- [x] Confirm project templates still do not select `bound-push`; if so, record a no-change disposition and do not add policy prose/defaults to templates or capability fixtures.
- [x] Run focused regression in owner-scoped groups plus the unchanged finish cases (avoid repeating identical tests):
  `uv run --locked --no-sync pytest -q tests/test_config.py tests/test_hooks.py tests/test_rendering.py tests/test_team_sources.py tests/test_workflow.py::test_github_scm_downloads_each_matrix_receipt tests/test_workflow.py::test_github_scm_rejects_missing_receipt_in_matrix tests/test_workflow.py::test_github_scm_rejects_tampered_receipt_in_matrix tests/test_workflow.py::test_receipt_matches_root_check_manifest tests/test_workflow.py::test_receipt_artifact_policy_does_not_drift_bindings tests/test_workflow.py::test_empty_gates_cannot_bypass_merge_and_ci`
- [x] Run `openspec validate proportionate-push-policy --strict --no-interactive`, update completed task evidence honestly, run documentation impact/disposition for the three canonical targets, reserve `ai-dlc project check --required` for the finalized archived delivery revision as the mandatory pre-merge gate.
- [x] Request whole-branch review and resolve actionable findings. Full required verification runs on the final archived delivery revision before merge. Archive and exact-merge finish remain subsequent delivery gates above.
- [x] Commit documentation/evidence as `docs: explain proportionate push policy` (and archive bookkeeping separately when the delivery branch is ready).

## Observed uncertainties to resolve at execution

1. **#176 baseline:** current `main` is `abd1c2a`; #176 is still on `codex/behavioral-check-onboarding` at `3f06895`. Its anticipated overlap is limited to `docs/development-workflow.md` and `docs/catalog.toml`, but the merged bytes and mapping order must be treated as authoritative.
2. **Partial rendering:** the proposed interface scopes policy prose to the resolved `clients` list for the current render. If repository expectations require shared AGENTS prose to reflect every project-selected client even during `--client` renders, pin that behavior with one test before implementing; do not infer it silently.
3. **Association syntax:** an absent `artifacts.branch` is a determinate nonmatch; a present non-string or blank branch is indeterminate and denies. This is stricter than the current Pydantic field shape for blank strings and intentionally protects the lightweight exemption.
4. **Inventory path safety:** use `inside` before reading inventory entries. If platform behavior for a `.toml` directory differs, use a symlinked entry to prove the same fail-closed path without adding an abstraction.

Execution grouping: Task A combines configuration and conditional guidance (Tasks 1 and 3) under one owner because their team-source tests overlap. Task B owns the offline hook decision (Task 2). Controller owns canonical docs, mappings and delivery (Task 4). Implementers stage only owned files; controller serializes commits.

Observed integration evidence: Task A `8d292af` passed 207 configuration/rendering/team-source tests and independent review. Task B `ba437d4` passed 34 real-Git hook-service tests and independent review. Six existing finish/receipt regressions passed; generated assets, layout and whole-project type checking passed. These are automated service fixtures, not a native-client qualification. Full required verification remains the subsequent delivery gate on the archived branch.

Whole-branch review at `e903e79` found one malformed-provider exception path. Fix `290207c` passed all 38 hook tests, focused Ruff and scoped independent review with no new findings. Required full verification remains pending on the archived delivery revision; archive does not imply merge or finish.
