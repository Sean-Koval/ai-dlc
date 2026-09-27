## 1. Bound resolution and isolated execution

- [x] 1.1 Add real temporary-Git cases for target advancement, unavailable merge object, unmerged/wrong-repository PR, historical record mismatch, dirty caller files and paths containing spaces/non-ASCII characters; mock only remote transport boundaries.
- [x] 1.2 Add the explicit CLI `--at-merge` option and bounded work-service helper using existing SCM resolution, work validation and platform-safe owned-worktree operations; preserve plain finish behavior and refuse implicit fetch/merge/rebase/push/archive actions.
- [x] 1.3 Resolve caller-relative handoff/learning/state inputs before checkout creation, validate historical identity, use merged repository authority and retain caller local bindings/credentials and ordinary operation-journal identity without copying secrets.

## 2. Gates, recovery and cleanup

- [x] 2.1 Invoke existing finish gates in the owned exact-merge checkout and cover failing CI/spec/deployment evidence, explicit no-spec work, unavailable historical policy and pending handoff.
- [x] 2.2 Add interruption-after-possible-transition, repeated invocation and concurrent-helper cases; reuse existing completion correlation and fresh remote reconciliation rather than duplicate transitions or skip evidence.
- [x] 2.3 Implement non-secret owned-resource recovery metadata and safe cleanup; cover successful removal, blocked-gate cleanup, missing/foreign ownership, symlink ambiguity, unexpected changed files and deletion failure without forced removal.
- [x] 2.4 Verify cleanup status remains separate from the actual finish outcome and cleanup recovery never repeats completion; verify caller HEAD/index/content and configured local-state location remain unchanged.

## 3. Guidance and delivery

- [x] 3.1 Update plain-finish remedies, canonical workflow/tool map and applicable generated guidance to offer the explicit helper and retain manual detached-checkout recovery.
- [x] 3.2 Record real local Git fixture results and clearly label mocked remote evidence; measure actual command reduction before updating delivery-friction claims. Live tracker qualification requires an explicitly authorized sandbox.
- [x] 3.3 Complete specification/work-record and affected-document review, record required content-bound dispositions, strictly validate this change and resolve actionable review findings. Run the full prepared required checks on the finalized archived delivery revision as the mandatory subsequent pre-merge gate.

## Subsequent delivery gates

After implementation and the checklist above are complete, archive this independently owned change on its bound delivery branch with `ai-dlc work archive`. Repair moved artifact links and any evidence targets actually made stale by archival. Immediately before authorized merge, update from the target branch and refresh required checks/evidence. Finish through `ai-dlc work finish` against the exact merged revision and its configured receipts. These remain mandatory later delivery gates, not checkboxes that must falsely claim post-merge completion before archive. No package publication or paid comparison is authorized by this task list.


# Exact-merge finish implementation plan

> Execute with bounded subagents and independent review. #177 merged as `05ab789`; this plan is now part of the active change.

**Goal:** implement #178's explicit `work finish WORK_ID --at-merge` by composing ordinary finish.
**Architecture:** one local owned-worktree module, one WorkService orchestration method, thin CLI dispatch. The historical project supplies policy; the caller supplies local configuration selection and the ordinary journal.
**Tech stack:** existing Python, `run_git`, `project_write_lock`, atomic filesystem helpers; no new dependency.
**Spec:** `openspec/changes/finish-merged-checkout/{design.md,tasks.md,specs/spec-delivery-traceability/spec.md}`.
**Basis:** focused inspection at main `56a5795`; preflight.md remains background, with corrections below. No tests or remote actions performed for this plan.

## Constraints and rulings

- Start only after #177 merges; parent refreshes the small affected-source diff before implementation.
- Only new public interface: `--at-merge`. No fetch, branch mutation, prune, forced removal, extra recovery command, generic resource framework, or parallel completion engine.
- Existing `Journal.begin` does NOT serialize pending transitions. Protect helpers with `project_write_lock(verified_common_git_dir)` for the entire helper, including inner finish and cleanup.
- Lock order: common Git directory, caller checkout, historical checkout. Reuse existing lock implementation unchanged. Linked caller worktrees therefore share protection even when explicit state directories differ.
- Keep caller lock during caller validation and helper orchestration. A helper must never acquire common lock while already holding caller lock elsewhere. Service construction releases its ordinary lock before helper entry.
- `load(work_id, mutation=True)` calls `save()`! Caller preflight must use a focused read-only reviewed-record helper: `_check_source()`, `inside`, TOML read, `resolve_work(..., require_review=True)`; never caller `save` or mutation-load.
- Retain raw authored identity separately from resolved record. Compare raw ID, PR, tracker, providers and bindings between caller and historical tree; independently validate both records against their respective runtime configurations. Also compare validated resolved provider selections and binding fingerprints: legacy records may omit their authored provider/binding tables, so raw equality alone does not prove the same completion identity. Do not require equal spec/plan paths across archival.
- Ordinary historical `finish` still performs its normal load/save. If normalization dirties that owned tree, retain it and report cleanup recovery; do not alter finish, restore the record, or force cleanup to hide this behavior.
- A common-Git-dir lock serializes helpers for one local repository, not separate clones or simultaneous ordinary finish. Do not claim broader guarantees or change ordinary finish for this slice.

## Exact shared local API (owned by implementer A)

New `src/ai_dlc/work/merge_checkout.py`; all Git calls use `run_git`.

```python
def repository_common_dir(root: Path) -> Path: ...
def require_merge_commit(root: Path, revision: str, repository: str) -> None: ...

@dataclass(frozen=True)
class CleanupResult:
    status: Literal["removed", "recovery-required"]
    locator: str | None = None
    reason: str | None = None
    remedy: str | None = None

@dataclass(frozen=True)
class OwnedMergeCheckout:
    root: Path
    revision: str
    marker: Path
    # private ownership fields may be added, never config/provider objects
    def create(self) -> None: ...
    def cleanup(self) -> CleanupResult: ...

def allocate_checkout(*, caller_root: Path, common_dir: Path, state_dir: Path,
                      work_id: str, revision: str) -> OwnedMergeCheckout: ...
def recover_checkout(*, marker: Path, common_dir: Path) -> CleanupResult: ...
```

- `repository_common_dir` verifies Git common-directory identity with absolute output and filesystem guards; reject ambiguous symlink/reparse identity, including replaced components. Recheck identity after acquiring its lock.
- `require_merge_commit` accepts only full hexadecimal SHA-1/SHA-256 IDs, proves commit peeling resolves to that exact ID, and refuses absent/noncommit objects with trusted repository + revision remedy. No named-ref/reachability requirement.
- `allocate_checkout` creates a unique private envelope under `state_dir/merge-checkouts/`, nonexistent `checkout` child, and atomic mode-0600 intent marker outside the child; returns before `git worktree add`. Parent namespace/envelope must be private and symlink/reparse safe using existing platform primitives.
- Marker schema 1: random resource ID, work ID, revision, caller/common-dir identity, envelope/checkout paths and filesystem identities, phase (`allocated`, `creating`, `ready`). No settings, credentials, provider responses, inputs, or remote completion claims.
- `create` records creating before Git, then performs `worktree add --detach`; verifies registration in the same common dir, exact detached HEAD, clean tracked/untracked/ignored content, and filesystem identities before recording ready. Do not change process cwd.
- `cleanup`/`recover_checkout` share one validator and removal implementation. Verify marker, private containment, recorded identities, registration, detached SHA and clean content before nonforced `worktree remove`; never broad prune or recursive removal.
- After confirmed Git removal, remove only verified marker and empty envelope. Partial creation with absent checkout/registration can remove the verified empty envelope; ambiguous partial state is recovery-required.
- Cleanup is local-only, idempotent for verified already-removed resources, and returns a recovery result for expected filesystem/Git refusal. Missing/foreign marker or replaced path is never deletion authority. Catching cleanup failure must not mask the original finish exception.
- `recover_checkout` is internal API only; recovery text names the marker and retained checkout, advises inspecting changes, and retains documented manual nonforced cleanup. It never opens a WorkService or tracker.

## WorkService contract and configuration ruling (owned by implementer B)

- Add `finish_at_merge(self, work_id, handoff: str | None = None, learning: str | None = None) -> dict` in `work/workflow.py`.
- `from_project` captures explicit `machine` as an absolute caller-cwd path before resolution; retain privately on service. Normalize explicit/default state directory to absolute caller-cwd meaning at construction, preserving ordinary journal location.
- A direct `WorkService(root, config, ...)` has no source-layer provenance. Before helper use, re-resolve caller runtime with retained machine selection and require equality with `self.config`; refuse nonreproducible custom injected configurations with remedy to use `from_project`. Do not reverse-engineer machine layers from merged config.
- The same reproducibility check detects enrollment/config changes after construction. Enrollment remains resolved through existing verified personal/profile/machine rules; no copied files or invented personal override API. Recheck after preparing the historical service, before mutation, to catch local-layer drift during preparation.
- Private `_merge_service(self, root: Path) -> WorkService` calls `WorkService.from_project(root, machine=self._machine, state_path=self._journal_path.parent)` with a fresh Registry. Tests may override this factory only to replace transport adapters; production never reuses caller Registry/root-sensitive providers.
- Historical `ai-dlc.toml` must exist and parse; `from_project` alone can otherwise fall back to defaults. It supplies gate/receipt authority even if caller tracked policy differs. Compare historical/current identity, not their entire project configs.
- Flow under locks: read-only caller reviewed validation → caller SCM `merged(bound_pr)` → exact local object check → allocate → try create → historical service/read-only validation/raw identity comparison → unchanged `historical.finish(work_id, handoff, learning)` → finally cleanup.
- Merge lookup is preflight only. Never inject it into inner finish: inner SCM merge lookup, gates, remote read and canonical journal reconciliation all run freshly.
- On a returned finish result, append `cleanup = dataclasses.asdict(cleanup_result)` without altering status/evidence (including blocked and completed,handoff_pending).
- On exception/interruption, attempt cleanup; re-raise original exception with recovery details attached as an exception note and `cleanup` attribute. CLI must visibly include recovery locator for failure paths; do not relabel an uncertain transition successful or wrap it as a preflight refusal.

## Executable task split and file ownership

### A — owned local Git lifecycle (FMC-01/02/04/05)

**Own only:** new `src/ai_dlc/work/merge_checkout.py`, new `tests/test_merge_checkout.py`.
- [x] Write failing real-Git tests for older/unreferenced exact commit, absent/invalid/tag object, detached registration, spaces/non-ASCII paths, dirty/staged/untracked caller and unrelated worktree preservation.
- [x] Write failing ownership tests: ordinary removal, add failure before/after registration, recovery retry, missing/foreign marker, replaced inode, symlink/reparse path, changed HEAD, tracked/untracked/ignored dirt, remove failure. Assert no force/fetch/prune and no unrelated filesystem changes.
- [x] Run focused tests to observe failures; implement API above; rerun focused tests and existing Git-runner enforcement. Report API ready to B without editing shared files.
- [x] Verify marker contains only allowlisted fields, modes/private boundaries, and truthful phase after interruption. Check ready cleanup and partial cleanup independently of any workflow object.

### B — historical orchestration and concurrency (FMC-01/02/03/04/05)

**Own only:** `src/ai_dlc/work/workflow.py`, new `tests/test_finish_merged_checkout.py`.
- [x] Write failing real-Git tests with mocked remote transport: advanced target selects merge, historical policy wins, missing/conflicting raw identity refuses, current binding drift/unmerged/wrong-target PR refuses, no-spec retains ordinary gates.
- [x] Assert caller work-record bytes/index/HEAD remain unchanged even with noncanonical TOML formatting; assert ordinary historical normalization is not hidden and dirty owned resource is retained with separate status.
- [x] Cover CI/spec/deployment blocks, successful cleanup, cleanup failure plus completed/blocked/exception outcomes, and interruption after possible tracker transition followed by fresh-gate reconciliation with same op_id/journal.
- [x] Cover explicit relative machine/state selection from cwd different from project root, enrolled local layers, unavailable historical config, config drift during preparation, unsupported direct injected config, and fresh Registry rooted in the historical tree.
- [x] Add process-level concurrent helpers from two linked caller worktrees with shared fake remote transport state: separate resource IDs, fresh gates twice, exactly one transition, shared lock despite distinct explicit state directories. Use controlled synchronization and real locks, not timing-only sleeps or threads (global in-process RLock could conceal wrong lock identity).
- [x] Run failing focused tests; implement orchestration against A's exact API; rerun focused tests plus existing ordinary-finish/reconciliation tests. Do not edit A's module or tests; request interface changes through parent.

### Parent — CLI, guidance, integration and delivery (TR-04; all FMC integration)

**Own:** `src/ai_dlc/cli.py`, `src/ai_dlc/providers/openspec.py`, `src/ai_dlc/harness/agents.py`, existing CLI/workflow/generated tests, canonical/template guidance, formal task checklist and documentation dispositions.
- [x] Add `at_merge: bool = False`; read handoff/learning files in caller context before dispatch, select exactly one service method, preserve plain finish. Render exception recovery details while preserving original failure semantics.
- [x] Add CLI tests for explicit dispatch, plain compatibility, relative file inputs, and failure recovery locator; update revision-mismatch remedy test to require helper plus manual command.
- [x] Update only canonical workflow/tool-map and applicable template/generated guidance; regenerate with existing tools. Review delivery-friction evidence without claiming unmeasured savings.
- [x] After A/B join, inspect cross-interface handling and the focused tests that exercise both implementations. Reserve the full required check run for the clean archived delivery revision. Review exact lock ordering, raw identities versus policy, local-layer provenance, interruption, and retained normalization dirt before marking formal tasks done.
Subsequent delivery: complete repository-required documentation dispositions, specification validation, archive, review, fresh target/full required checks, authorized merge and exact-merge finish. Do not delegate remote mutations implicitly. This plan itself supplies no qualification evidence.

## Review focus and implementation rulings to retain

- Caller mutation during validation is forbidden; B's byte-for-byte record test must catch accidental mutation-load.
- Historical normalization may leave owned dirt; B must keep genuine finish result and A must refuse deletion.
- Config provenance cannot be reconstructed from effective values; B must refuse unsupported direct configuration instead of silently changing bindings.
- Concurrent linked worktrees with different state paths must share common-dir protection; B's process test must expose the old pending-journal race.
- Partial Git add and ignored content can evade simplistic cleanup; A's partial-registration and ignored-file tests must retain ambiguous resources.
- No user permission ruling is outstanding. Parent may adjust internal names before dispatch; changes to ordinary-finish semantics, new public commands, or broader concurrency scope require revisiting the formal scope first.

## Observed implementation evidence

CLI/guidance `30e6209` passed 94 CLI/phase/remedy tests and 418 rendering/template tests. Lifecycle `d751b90` with recovery fix `b4d9666` passed 28 real-Git lifecycle tests plus six shared Git-runner checks. Service `c31644e`, identity fix `c7f6715` and historical-policy ownership fix `9a0766c` passed 26 helper tests, including spawned-process concurrency; affected existing finish/reconciliation checks passed. Formatting, lint, types, generated assets, layout, work validation and strict change validation passed during integration. Counts are scoped groups, not a full-suite total.

Independent task reviews and whole-branch review are complete. Two lifecycle recovery findings, inferred identity/malformed-record findings and the final external historical-policy symlink finding were reproduced and corrected; scoped re-reviews passed without open findings. Windows helper execution is added to hosted core CI and remains an explicit delivery gate. Remote SCM/tracker outcomes are mocked; native desktop/client and live-provider qualification are not inferred.

Full required verification remains mandatory on the finalized archived delivery revision before merge. Exact-merge CI and AI-DLC finish follow merge. No numerical command, time or token saving was claimed or added to the historical baseline.
