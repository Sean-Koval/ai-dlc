## MODIFIED Requirements

### Requirement: TR-04 Explained merged-revision specification gate
The specification gate SHALL continue to require a checkout that is exactly the pull request's merged revision with a clean specification tree. When it refuses, the blocked reason SHALL name the expected merged revision, the revision the checkout actually holds and the remedy. An unreadable checkout revision and a dirty specification tree SHALL be reported as distinct reasons. Canonical and generated delivery guidance SHALL describe finishing work after the target branch has moved past the merge, including explicit `work finish WORK_ID --at-merge` and manual detached-checkout recovery. The helper SHALL not change the gate applied to its evidence checkout or the refusal behavior of plain finish.

#### Scenario: The target branch moved past the merge
- **WHEN** plain finish runs from a checkout that is not the merged revision
- **THEN** the blocked reason names both revisions and offers the explicit at-merge helper or a temporary detached checkout at the merged revision, and no tracker state changes

#### Scenario: The merged revision is checked out with dirty specification files
- **WHEN** the checkout used by the specification gate is the merged revision but specification files are modified or untracked
- **THEN** the gate refuses with a dirty-tree reason naming that revision rather than a revision mismatch

#### Scenario: Guidance describes the procedure
- **WHEN** a person or agent reads canonical delivery guidance, or generated guidance for the applicable OpenSpec, SCM and tracker selection
- **THEN** it explains explicit at-merge finishing and the manual fallback of preparing a temporary detached checkout at the merge commit, finishing there and removing it afterwards

#### Scenario: An active change is reported before merge
- **WHEN** local work status or PR preparation sees an active OpenSpec change
- **THEN** it reports active change, archive before merge; status requires no network call

#### Scenario: The gate names the archive remedy
- **WHEN** required specification evidence still references an active change
- **THEN** finish names work archive on the delivery branch or a linked follow-up pull request without relaxing its gates

#### Scenario: Archive commits only its selected work
- **WHEN** work archive runs for a reviewed record and its own active change
- **THEN** the adapter archives and promotes it, the service repoints spec and a contained plan, and commits only affected specification files and the record

## ADDED Requirements

### Requirement: FMC-01 Explicit bound merged-revision resolution

The CLI SHALL expose `work finish WORK_ID --at-merge` through a shared work application service. The helper SHALL validate the caller's selected record and bindings and resolve its bound PR's authenticated merge SHA through the configured SCM. It SHALL require the configured repository/target identity and the exact commit object locally. Missing/unmerged/mismatched PRs, binding drift, ambiguous work or unavailable objects SHALL refuse with an actionable reason before tracker mutation. It SHALL NOT choose current target HEAD as a substitute, fetch implicitly, or merge, rebase, push, archive or repair CI.

#### Scenario: Main has advanced since the bound PR merged
- **WHEN** at-merge finish resolves a merged PR whose commit is locally available and older than current main
- **THEN** it selects that exact authenticated merge commit rather than current main and proceeds to isolated validation

#### Scenario: A required object or PR identity is unavailable
- **WHEN** the bound merge object is missing or the PR is unmerged or belongs to another repository or target
- **THEN** it stops before tracker mutation and, for a missing object, names the trusted repository/revision fetch remedy without silently selecting another commit

### Requirement: FMC-02 Isolated evidence preserves caller and local authority

The helper SHALL create a uniquely owned detached checkout at the authenticated merge SHA and use the merged repository's policy and matching historical work identity as evidence authority. It SHALL preserve the caller's HEAD, index, tracked and untracked content, explicit local configuration/credential references and canonical operation-journal identity. Relative explicit input/state paths SHALL retain their caller-relative meaning. It SHALL refuse missing or conflicting historical work/provider identities and SHALL NOT copy current tracked policy or credential values into the isolated checkout to make it pass.

#### Scenario: Caller has unrelated dirty work
- **WHEN** at-merge finish runs from an advanced checkout containing modified and untracked files while its work/provider identity is valid
- **THEN** isolated evidence uses the bound merged revision and every caller file, index entry and HEAD remains unchanged

#### Scenario: Historical and current record identities disagree
- **WHEN** the merged checkout lacks the selected record or binds a different PR, tracker or provider identity
- **THEN** the helper refuses before completion rather than rewriting the historical record or retargeting work

#### Scenario: Explicit local state and handoff inputs are configured
- **WHEN** the caller supplies local bindings, an operation-state location or a relative file-based learning/handoff input
- **THEN** the helper retains that input's original meaning, existing credential resolution and ordinary completion journal identity without persisting secret values in its temporary tree

### Requirement: FMC-03 Existing finish gates remain authoritative

At-merge finish SHALL invoke the existing finish service against the isolated evidence checkout and require the same current specification, authenticated merged PR, exact merged-manifest CI receipts and configured deployment gates as ordinary finish. It SHALL preserve explicit no-spec behavior, remote tracker reconciliation and handoff-pending semantics. Neither successful checkout preparation nor an earlier journal result SHALL substitute for fresh gate evaluation.

#### Scenario: Merged CI or specification evidence fails
- **WHEN** the owned checkout is created but a required gate fails or is unavailable
- **THEN** finish remains blocked with the existing gate reasons, the tracker is unchanged and temporary-resource cleanup is attempted safely

#### Scenario: A record deliberately requires no specification
- **WHEN** the reviewed historical record records no-spec with its reason
- **THEN** existing no-spec semantics apply while the merged PR, CI and other configured gates remain required

#### Scenario: A successful finish cannot write its handoff
- **WHEN** completion succeeds but the knowledge operation is unavailable
- **THEN** the original completed-with-handoff-pending result remains visible and a retry follows existing missing-handoff reconciliation

### Requirement: FMC-04 Interrupted retries preserve correlation and uncertainty

The helper SHALL retain non-secret owned-resource recovery metadata outside the temporary checkout, reuse the ordinary completion correlation and journal, and reconcile remote state through existing finish behavior on retry. Interruption or a lost provider response SHALL NOT be relabeled successful or authorize an unverified duplicate transition. Concurrent invocations SHALL use existing operation protection with distinct owned checkout resources and SHALL NOT race shared cleanup or repeat a confirmed completion transition.

#### Scenario: A transition succeeds but its response is lost
- **WHEN** the first helper invocation is interrupted after a possible tracker transition and is retried
- **THEN** fresh gates and remote reconciliation determine the result using the same completion identity rather than blindly issuing another transition

#### Scenario: Two helpers finish the same work
- **WHEN** concurrent invocations reach completion for the same bound work
- **THEN** existing locking and reconciliation permit no duplicate confirmed transition and each invocation manages only its own checkout

### Requirement: FMC-05 Cleanup is owned and independent of completion

The helper SHALL attempt to remove only its verified owned clean checkout after success, blocked gates or interruption when cleanup is possible. Foreign paths, changed content, symlink/ownership ambiguity or cleanup errors SHALL be retained with a safe recovery locator and reported separately from the known completion outcome. It SHALL NOT force-delete user changes or change a successful remote completion into a false failure. Retrying cleanup of a verified owned resource SHALL NOT itself repeat completion.

#### Scenario: Normal finish completes and cleanup succeeds
- **WHEN** existing finish succeeds and the owned isolated checkout remains clean
- **THEN** the temporary checkout is removed and the result reports completion with successful cleanup

#### Scenario: Cleanup cannot safely remove the resource
- **WHEN** the temporary checkout has unexpected changes or removal fails
- **THEN** the result retains the actual finish outcome, identifies the remaining owned resource and recovery action, and does not force-delete it

#### Scenario: Recovery metadata points at a foreign path
- **WHEN** cleanup cannot verify the path's ownership or containment
- **THEN** cleanup refuses without modifying the foreign path or repeating a tracker operation
