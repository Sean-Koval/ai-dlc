## ADDED Requirements

### Requirement: TR-01 Explicit traceability

New delivery guidance SHALL map product requirement IDs to formal behavioral scenarios when needed, a deliverable work item, and verification. Scope, rationale, spec, and task list SHALL retain distinct ownership.

#### Scenario: A feature is decomposed
- **WHEN** one outcome needs independently releasable behavior changes
- **THEN** each ticket has explicit requirement references, dependencies, exclusions, and acceptance while each required OpenSpec change can finish independently

### Requirement: TR-02 Valid dependency graph

Work validation SHALL reject missing or cyclic dependencies and absent referenced artifacts before publication; start SHALL refuse incomplete or unavailable required dependency status.

#### Scenario: A ticket depends on itself
- **WHEN** the local dependency graph contains a cycle
- **THEN** validation fails without creating or updating a tracker item

#### Scenario: Validation is local and proportional
- **WHEN** a selected work item has local document references and an unrelated draft record is invalid
- **THEN** read-only validation inspects the selected reachable dependency closure and local artifacts without creating a mutation journal, probing external references, or rejecting the unrelated draft

#### Scenario: A prerequisite is not completed
- **WHEN** a required dependency is unpublished, cancelled, duplicate, incomplete, or unavailable through its pinned provider
- **THEN** start refuses before creating a branch, saving work bindings, or mutating the tracker, without treating a terminal non-completion state as completed

### Requirement: TR-03 Compatible rich publication

New issue publication SHALL include scope, references, dependencies, and acceptance while preserving existing correlation/idempotency and authored descriptions on repeat publication.

#### Scenario: A published item is retried
- **WHEN** the same work record already has a tracker binding
- **THEN** publication reuses the existing issue and does not overwrite its authored description


#### Scenario: A historical creation attempt is retried
- **WHEN** the publication journal uses an older body and the issue is mapped or recoverable by correlation or the recorded result
- **THEN** publication preserves the old operation identity and payload fingerprint, reuses the issue without replacing its authored body, and an uncertain missing result never authorizes a duplicate create


#### Scenario: A legacy work item uses a provider-native specification ID
- **WHEN** validation or repeat publication reads a specification identifier, including an opaque slash ID or provider URI
- **THEN** the identifier remains provider-owned, the mapped issue is reconciled unchanged, and explicit local specification documents still require safe existing paths
