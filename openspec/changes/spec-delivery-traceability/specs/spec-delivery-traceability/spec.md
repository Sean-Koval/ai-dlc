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

### Requirement: TR-03 Compatible rich publication

New issue publication SHALL include scope, references, dependencies, and acceptance while preserving existing correlation/idempotency and authored descriptions on repeat publication.

#### Scenario: A published item is retried
- **WHEN** the same work record already has a tracker binding
- **THEN** publication reuses the existing issue and does not overwrite its authored description
