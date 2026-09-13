## MODIFIED Requirements

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
