## ADDED Requirements

### Requirement: GT-01 Capability-based lifecycle
Work start SHALL consume declared tracker lifecycle capabilities without provider-name branching. Discovery SHALL be optional for legacy adapters, with explicit unverified fallback only when discovery is not declared. Declared discovery failures SHALL fail visibly.

#### Scenario: A tracker cannot represent in-progress
- **WHEN** a reviewed work item starts with that capability unavailable
- **THEN** local work starts while the remote ticket is read unchanged and the unsupported transition is reported

#### Scenario: Discovery fails
- **WHEN** a declared capability operation fails validation or transport
- **THEN** work does not substitute legacy transition behavior

### Requirement: GT-02 Optional project planning states
GitHub Issues SHALL work without Projects. A configured Project SHALL use explicitly mapped single-select status options, preserving issue identity and distinguishing native issue state from planning state. Start SHALL not reopen or overwrite a terminal issue as a side effect.

#### Scenario: Work uses a configured Project
- **WHEN** an open issue starts with a valid in-progress mapping
- **THEN** the selected project item moves to that option while the issue remains open and both states are observable

#### Scenario: Configuration is incomplete or stale
- **WHEN** a selected project, field or mapped option cannot be verified
- **THEN** the operation fails rather than silently falling back to issue-only behavior or guessing a status by name

### Requirement: GT-03 Identity and uncertain recovery
Issue and project operations SHALL verify configured identity, refuse incomplete or ambiguous reconciliation, and preserve uncertainty across partial issue/project writes. A Project Done status SHALL NOT independently establish work completion or bypass finish gates.

#### Scenario: Issue creation succeeds but project attachment fails
- **WHEN** publish is retried
- **THEN** it reuses the correlated issue and reconciles project membership without creating another issue

#### Scenario: A teammate closes as not planned
- **WHEN** the adapter reads that ticket
- **THEN** it does not report successful normalized completion

### Requirement: GT-04 Explicit reusable setup
Scaffold/adopt SHALL accept an explicit tracker selection while preserving omitted-option defaults. Guided connection SHALL discover named authorized repositories/projects/fields/options and save an exact non-secret configuration plan, refusing drift before apply. Credentials and machine paths SHALL stay local.

#### Scenario: A user selects GitHub Issues with a Project
- **WHEN** they provide or choose the authorized repository and Project and review discovered status mappings
- **THEN** AI-DLC prepares that configuration without manual ID lookup, source edits or installation of Plane

#### Scenario: Enrollment changes after connection preview
- **WHEN** the effective personal or machine provider/account configuration changes after preview
- **THEN** connection apply refuses the stale plan and inherited work bindings remain protected

### Requirement: GT-05 Portable selected migration
Default-only switches SHALL preserve retained effective work bindings. Selected migration SHALL verify selected targets, preserve unselected work and non-tracker references, and record source-to-target provenance. Remote issue creation SHALL require a separately reviewed exact plan and SHALL NOT be an implicit rebind side effect.

#### Scenario: A project changes tracker
- **WHEN** its default or selected work moves to another configured supported tracker
- **THEN** the same provider-independent migration rules apply and SCM/PR/CI configuration and completion gates remain unchanged

#### Scenario: Target identity differs from the configured destination
- **WHEN** a target read observes a different configured account or project/team identity at preview or apply
- **THEN** the provider rejects that target before migration writes local bindings

#### Scenario: A local batch apply is interrupted
- **WHEN** selected work writes fail or an external replacement prevents safe rollback
- **THEN** migration retains before/after recovery evidence, preserves external replacements and reports recovery-required rather than claiming success

### Requirement: GT-06 Evidence boundaries
Qualification SHALL distinguish fixture tests, offline setup, live reads and live mutations, and report missing access or unsupported providers without claiming full portability.

#### Scenario: No live destination is supplied
- **WHEN** implementation checks pass
- **THEN** the result identifies unverified live setup and mutation gates and does not claim an actual migration
