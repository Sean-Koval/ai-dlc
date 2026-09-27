# Finish merged checkout design

## Context and authority

[Product direction](../../../docs/product-direction.md) favors existing tools and smaller delivery overhead. TR-04 requires exact merged-revision specification evidence and documents manual detached-worktree recovery. `WorkService.finish` already checks merged PR identity, CI and specification state before reading and transitioning the tracker; its journal reconciles uncertain completion and pending knowledge writes. `WorkService.from_project` resolves local bindings and an explicit state path. The helper must compose these boundaries, not introduce another completion engine.

## Entry point and flow

The only new public interface is `ai-dlc work finish WORK_ID --at-merge`, compatible with existing handoff/learning options. Plain finish retains its behavior. Resolve file-based inputs relative to the caller before moving execution context and keep them in memory or existing controlled local storage; do not copy secrets into the temporary tree.

1. Read and validate the caller's selected record and configured provider identities under existing lock/configuration rules. Resolve the PR through its bound SCM and require its authenticated merged SHA, configured repository and target branch. Reject a missing/unmerged/mismatched PR, ambiguous record or drifted binding. This phase is read-only toward remote systems.
2. Require that exact commit object locally. If unavailable, give a bounded fetch remedy naming the trusted repository/revision and stop before worktree creation or tracker mutation; this slice does not add fetch orchestration.
3. Create a uniquely owned detached Git worktree at the verified SHA in controlled local temporary storage. Never reuse an arbitrary directory or force overwrite. Retain non-secret ownership/recovery metadata outside the worktree so an interrupted run can identify only its own resource.
4. Load repository authority from the merge checkout, validate that its work record binds the same work ID, PR, tracker and provider identities, and resolve the caller's explicitly selected local bindings and credential references through existing configuration rules. Do not copy the caller's current tracked policy into the historical checkout. Reject unavailable historical records, identity mismatch or unsafe local resolution. Relative explicit state/input paths retain their original meaning. Use the same canonical operation-journal path and completion correlation as ordinary finish, not a temporary independent journal.
5. Invoke the existing finish service against that checkout. All gates, exact manifest receipts, configured deployment checks, remote reconciliation and handoff semantics remain authoritative. A local completed journal never authorizes skipping fresh evidence.
6. Remove only the owned worktree when safely clean. Return the finish result plus separate cleanup status. If cleanup fails or the owned tree unexpectedly contains user changes, retain it with a safe recovery instruction; do not force-delete. An interrupted call records a recovery locator without inventing a completed or failed remote outcome.

## Retry and ownership

A retry resolves the current bound remote state and reruns existing gates. Reuse the caller's ordinary completion operation identity and journal so an uncertain successful tracker write is reconciled rather than blindly repeated. Treat an already closed tracker and pending handoff through existing finish behavior. A cleanup retry may remove a verified clean owned resource without repeating completion; an absent or foreign ownership marker is a refusal, never permission to delete. Concurrent helpers use existing operation locks/correlation and separate owned checkout identifiers; at most one transition is allowed by the existing reconciliation boundary.

The helper must preserve caller HEAD, index and tracked/untracked content, including dirty specification files, because those are not the evidence tree. Caller configuration/record changes affecting identity still block preflight. The isolated evidence checkout itself must remain exactly at the authenticated SHA with clean specifications. Temporary storage is local implementation state, not portable profile authority, a new work record or a stored credential container.

## Trade-offs and compatibility

This is smaller than a pre-merge refresh command: no merge/rebase/push or command retries are added. It deliberately requires a locally available merged object and reports a precise remedy otherwise. It works for both specification-required and explicitly no-spec records, retaining their respective existing finish semantics. Existing platform-safe filesystem/locking support must be used; tests on one OS do not claim another is qualified.

## Verification and documentation

Use real temporary Git repositories to test target advancement, spaces/non-ASCII paths, detached identity, dirty caller preservation and cleanup ownership. Mock only remote SCM/tracker boundaries for failure/reconciliation tests, and label those fixtures. Test a timeout after a successful transition, duplicate invocation, pending handoff, configured state-path preservation, policy drift, missing object, dirty evidence tree and cleanup failure. An authorized sandbox walkthrough is separate evidence and is not required to publish this specification.

Update TR-04's guidance while retaining plain finish refusal. Review the canonical workflow, tool map and generated selected-capability instructions; update delivery-friction evidence only after measuring the actual helper. Record content-bound dispositions rather than manufacturing savings. No other proposed team-adoption change is a hard dependency.
