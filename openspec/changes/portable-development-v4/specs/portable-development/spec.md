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

#### Scenario: Offline tracker conformance follows delivered adapters
- **WHEN** a packaged offline GitHub Issues, Jira Cloud, or Plane target is selected
- **THEN** it runs the existing real adapter transport and shared lifecycle fixtures,
  including GitHub Projects behavior and the required packaged test helpers
- **AND** provider and all aggregates include those fixtures without duplicate paths
- **AND** missing fixtures fail explicitly and results remain offline-only; selecting
  an unavailable live scope cannot inherit offline success

### Requirement: Release bootstrap candidates bind verified artifacts
Candidate release manifests SHALL bind one engine wheel and hashed dependency constraints
by their actual SHA256 digests and an explicit HTTPS artifact base URL. Candidate generation
SHALL validate engine identity/version and SHALL NOT publish assets or overwrite an existing
manifest. Bootstrap SHALL reject corrupted downloads before installing the engine.

#### Scenario: A maintainer prepares candidate assets
- **WHEN** the wheel identity matches the requested engine version and constraints exist
- **THEN** generate a shell-safe manifest of exact filenames, HTTPS URLs and artifact hashes
- **AND** retain publication and live installation as separate verification obligations

#### Scenario: A candidate is ambiguous or stale
- **WHEN** multiple wheels, a mismatched wheel version or an existing output is supplied
- **THEN** refuse generation without replacing the existing manifest

#### Scenario: A release download is corrupted
- **WHEN** the wheel or constraints differ from the manifest digest
- **THEN** refuse engine installation and preserve the previously selected CLI
