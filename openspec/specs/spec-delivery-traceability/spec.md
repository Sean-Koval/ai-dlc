# spec-delivery-traceability Specification

## Purpose
Connect requirements, behavioral scenarios, deliverable work and verification through explicit links, valid dependency graphs and compatible rich tracker publication.
## Requirements
### Requirement: TR-01 Explicit traceability

New delivery guidance SHALL map product requirement IDs to formal behavioral scenarios when needed, a deliverable work item, and verification. Scope, rationale, spec, and task list SHALL retain distinct ownership.

#### Scenario: A feature is decomposed
- **WHEN** one outcome needs independently releasable behavior changes
- **THEN** each ticket has explicit requirement references, dependencies, exclusions, and acceptance while each required OpenSpec change can finish independently

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
The specification gate SHALL continue to require a checkout that is exactly the pull request's merged revision with a clean specification tree. When it refuses, the blocked reason SHALL name the expected merged revision, the revision the checkout actually holds and the remedy. An unreadable checkout revision and a dirty specification tree SHALL be reported as distinct reasons. Canonical and generated delivery guidance SHALL describe finishing work after the target branch has moved past the merge.

#### Scenario: The target branch moved past the merge
- **WHEN** finish runs from a checkout that is not the merged revision
- **THEN** the blocked reason names both revisions and directs the user to a temporary detached checkout at the merged revision, and no tracker state changes

#### Scenario: The merged revision is checked out with dirty specification files
- **WHEN** the checkout is the merged revision but specification files are modified or untracked
- **THEN** the gate refuses with a dirty-tree reason naming that revision rather than a revision mismatch

#### Scenario: Guidance describes the procedure
- **WHEN** a person or agent reads canonical or generated delivery guidance
- **THEN** it explains preparing a temporary detached checkout at the merge commit, finishing there and removing it afterwards

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

