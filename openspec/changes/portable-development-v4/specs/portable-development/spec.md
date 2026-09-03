## ADDED Requirements

### Requirement: Project environment and checks are repository-owned
The system SHALL prepare declared runtimes and ordered dependency steps and execute
required checks from one repository manifest. Machine settings SHALL NOT weaken checks.

#### Scenario: An interrupted setup is retried
- **WHEN** a dependency step fails after earlier steps succeeded
- **THEN** a retry verifies completed steps and resumes remaining work

#### Scenario: A check does not run successfully
- **WHEN** a required check is missing, cancelled, skipped or fails
- **THEN** its receipt SHALL NOT qualify as successful completion evidence

### Requirement: Completion uses trusted merged-revision evidence
The system SHALL verify the configured repository, target branch, workflow, merged
revision, configuration digests and required outcomes before completing a tracker item.

#### Scenario: An unrelated green workflow exists
- **WHEN** the workflow identity or checked revision differs
- **THEN** work completion is blocked with the failing gate identified

#### Scenario: Completion succeeds but handoff writing fails
- **WHEN** the tracker is closed and knowledge storage is unavailable
- **THEN** report completed with handoff pending and retry only the missing note

### Requirement: Configuration and content remain portable
The system SHALL separate base, personal, project and machine scopes, preserve existing
content during adoption/update, and verify provider and skill artifacts before loading.

#### Scenario: Generated content and user content both changed
- **WHEN** applying the update would overwrite an authored change
- **THEN** report the conflict without overwriting the destination

#### Scenario: A provider binding changes
- **WHEN** new work selects a different provider
- **THEN** existing records retain their bindings until explicitly mapped by rebind

### Requirement: Execution limitations are explicit
The system SHALL refuse unsupported required policies and unavailable provider-test
isolation. Local fixture tests SHALL NOT be represented as live platform verification.

#### Scenario: Docker is unavailable
- **WHEN** provider conformance testing is requested
- **THEN** report unavailable and do not execute the provider on the host
