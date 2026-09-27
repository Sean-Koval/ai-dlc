# spec-delivery-traceability Specification

## Purpose
Connect requirements, behavioral scenarios, deliverable work and verification through explicit links, valid dependency graphs and compatible rich tracker publication.
## Requirements
### Requirement: TR-01 Explicit traceability

New delivery guidance SHALL map product requirement IDs to formal behavioral scenarios when needed, a deliverable work item, and verification. Scope, rationale, spec, and task list SHALL retain distinct ownership. `work new` SHALL create a schema-valid unreviewed record from explicit fields or a configured tracker item without publication or mutation state. Existing records and unsafe IDs SHALL be refused without writing. Missing tracker content SHALL remain explicit TODO placeholders.

#### Scenario: A feature is decomposed
- **WHEN** one outcome needs independently releasable behavior changes
- **THEN** each ticket has explicit requirement references, dependencies, exclusions, and acceptance while each required OpenSpec change can finish independently

#### Scenario: A record is created from a tracker item
- **WHEN** an issue has an Acceptance or Acceptance criteria section with bullet lines
- **THEN** the new record carries those acceptance lines, its tracker reference and reviewed=false

#### Scenario: Missing issue content remains explicit
- **WHEN** an issue has no acceptance section
- **THEN** acceptance contains TODO: state acceptance and no content is invented

#### Scenario: Offline drafting
- **WHEN** explicit title, scope and acceptance are supplied without an issue
- **THEN** creation and validation need no provider call or state directory

### Requirement: TR-02 Valid dependency graph

Work validation SHALL reject missing or cyclic dependencies and absent referenced artifacts before publication; start SHALL refuse incomplete or unavailable required dependency status. A suffix-less specification reference whose leading path segment is an entry of the repository root SHALL be validated as a local artifact whether or not the referenced path currently exists. Every record under `.ai-dlc/work/` SHALL be validatable together, offline and without resolving provider bindings, so a dangling local artifact reference fails a required project check.

#### Scenario: A ticket depends on itself
- **WHEN** the local dependency graph contains a cycle
- **THEN** validation fails without creating or updating a tracker item

#### Scenario: Validation is local and proportional
- **WHEN** a selected work item has local document references and an unrelated draft record is invalid
- **THEN** read-only validation inspects the selected reachable dependency closure and local artifacts without creating a mutation journal, probing external references, or rejecting the unrelated draft

#### Scenario: A prerequisite is not completed
- **WHEN** a required dependency is unpublished, cancelled, duplicate, incomplete, or unavailable through its pinned provider
- **THEN** start refuses before creating a branch, saving work bindings, or mutating the tracker, without treating a terminal non-completion state as completed

#### Scenario: A referenced specification directory is moved
- **WHEN** a record's specification reference is a bare repository path such as an OpenSpec change directory and archiving has moved that directory
- **THEN** validation reports the artifact as absent rather than reinterpreting the reference as a provider-native identifier

#### Scenario: Every record is validated as a required check
- **WHEN** the repository-wide validation runs over `.ai-dlc/work/`
- **THEN** it reports each unreadable record, dangling local artifact and graph error together, resolves no provider binding, creates no journal, probes nothing outside the repository, and a finished record's historical fingerprint does not fail it

### Requirement: TR-03 Compatible rich publication

New issue publication SHALL include scope, references, dependencies, and acceptance while preserving existing correlation/idempotency and authored descriptions on repeat publication.

#### Scenario: A published item is retried
- **WHEN** the same work record already has a tracker binding
- **THEN** publication reuses the existing issue and does not overwrite its authored description

#### Scenario: A historical creation attempt is retried
- **WHEN** the publication journal uses an older body and the issue is mapped or recoverable by correlation or the recorded result
- **THEN** publication preserves the old operation identity and payload fingerprint, reuses the issue without replacing its authored body, and an uncertain missing result never authorizes a duplicate create

#### Scenario: A legacy work item uses a provider-native specification ID
- **WHEN** validation or repeat publication reads a specification identifier, including an opaque slash ID or provider URI, that is not anchored in the repository root
- **THEN** the identifier remains provider-owned, the mapped issue is reconciled unchanged, and explicit local specification documents and repository-anchored paths still require safe existing paths

#### Scenario: A local specification reference uses a file URI or dangling symlink
- **WHEN** a specification reference uses reserved file URI notation or identifies a dangling final or ancestor symlink
- **THEN** publication refuses before tracker effects rather than treating it as a provider-native identifier

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

### Requirement: TR-05 Provider identity excludes evidence policy
A provider identity fingerprint SHALL cover the configuration that determines which external service, branch and workflow runs a work record was reviewed against. It SHALL NOT cover receipt artifact policy, which the finish gate authenticates from the merged manifest rather than from the binding. An SCM configuration key that is not recognised evidence policy SHALL contribute to identity. Canonical delivery guidance SHALL describe this boundary without claiming the fingerprint authenticates receipts.

Binding drift refusals SHALL name the role, explain the different role configuration, and direct active work to review and refresh only its drifted binding before single-record validation and its next mutation. Finished records SHALL retain historical bindings and use `ai-dlc work validate --all`. Single-record CLI validation SHALL add a top-level hint repeating the remedy only when every error is binding drift. Repository-wide validation output SHALL remain unchanged.

#### Scenario: The CI receipt matrix changes
- **WHEN** the configured receipt artifact names change and a work record holds bindings from before the change
- **THEN** mutation proceeds without a binding drift refusal, and the finish gate still requires every receipt named by the merged manifest

#### Scenario: The trusted repository, branch or workflow changes
- **WHEN** the configured SCM repository, target branch or workflow changes
- **THEN** mutation refuses with provider binding drift until the record is reviewed again

#### Scenario: An unrecognised SCM setting changes
- **WHEN** an SCM configuration key that is not recognised receipt artifact policy is added or changed
- **THEN** mutation refuses with provider binding drift rather than treating the unknown setting as evidence policy

#### Scenario: Guidance describes the boundary
- **WHEN** a person or agent reads canonical delivery guidance on configured evidence and bindings
- **THEN** it states that the receipt matrix does not drift bindings and does not claim the fingerprint authenticates receipts

#### Scenario: Active record has binding drift
- **WHEN** a work mutation or single-record validation encounters a changed provider fingerprint
- **THEN** the refusal retains the leading `Provider binding drift for <role>` and explains reviewed active repair and historical-record validation without changing bindings

#### Scenario: Every validation error is binding drift
- **WHEN** single-record CLI validation reports only binding-drift errors
- **THEN** its JSON output includes a hint repeating the same remedy

#### Scenario: Historical records are checked together
- **WHEN** repository-wide validation checks finished records with historical bindings
- **THEN** its output and binding-independent validation behavior remain unchanged

### Requirement: TR-06 One command between delivery gates

`work start` and `work link` SHALL commit the record they edit, staging only `.ai-dlc/work/<id>.toml`, unless the caller disables the commit. `work pr <id>` SHALL open the pull request for the bound branch through the SCM role exactly once, render its body from the record, link the resulting URL as the `pr` artifact and commit the record. The SCM adapter SHALL refuse to open a pull request for a branch without an upstream and SHALL name the remedy rather than pushing implicitly.

#### Scenario: Start commits only its record
- **WHEN** reviewed work is started on a clean checkout
- **THEN** the working tree is clean afterwards and the newest commit is `chore(work): start <id>` touching only `.ai-dlc/work/<id>.toml`

#### Scenario: A pull request is opened once
- **WHEN** `work pr` runs for a started record on a pushed branch and runs again afterwards
- **THEN** the first call creates one pull request, links its URL and commits the record, and the second call prints the existing URL without sending another create

#### Scenario: The branch has no upstream
- **WHEN** `work pr` runs for a branch that has not been pushed
- **THEN** it refuses with the remedy to push the branch first, creates no pull request and changes no record

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

