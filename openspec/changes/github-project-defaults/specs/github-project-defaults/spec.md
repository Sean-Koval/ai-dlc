## ADDED Requirements

### Requirement: GP-01 Project-backed GitHub default
GitHub connection SHALL default to a Project named after the configured project,
or the selected repository name when no project name is configured. It SHALL infer
the repository from the selected provider or project SCM configuration when omitted.
The user MAY explicitly select issues-only behavior or a different existing Project.
Offline scaffolding SHALL NOT create remote resources.

#### Scenario: New connection uses the repository context
- **WHEN** the user previews GitHub setup without a Project selection
- **THEN** the plan targets the verified repository and owner and selects one exact matching Project or proposes its creation
- **AND** preview performs no remote or project-configuration writes

#### Scenario: Ambiguous or inaccessible Project selection
- **WHEN** Project discovery is incomplete, unauthorized, or returns multiple matching Projects
- **THEN** setup reports the problem and does not silently fall back to issues-only or create another Project

### Requirement: GP-02 Reviewed creation and repository association
Saved-plan apply SHALL recheck local configuration, effective runtime, retained work,
viewer, repository and owner before mutation. It SHALL create the selected missing
Project or reuse the verified existing one, associate it with the repository, and
configure the verified Status/Todo/In Progress/Done mappings. Custom workflows
SHALL require explicit existing-Project mappings when those defaults are unavailable.
Existing bound tracker aliases SHALL remain protected from implicit changes.

#### Scenario: Apply default setup
- **WHEN** a fresh default setup plan is applied
- **THEN** the Project is created at most once for the retained local operation, associated with the repository, and its actual field/option identities are saved
- **AND** the tracker default and old work bindings are not silently changed

#### Scenario: Create response is lost
- **WHEN** a Project create request has an uncertain result
- **THEN** the durable operation records uncertainty and retries refuse another create until the remote result is explicitly reconciled

#### Scenario: Creation succeeds but configuration fails
- **WHEN** a verified created Project is recorded and later local connection apply fails
- **THEN** retry reuses that recorded Project and does not create a duplicate

### Requirement: GP-03 Explicit compatibility
An explicit `--issues-only` connection SHALL avoid Projects requests. Prior saved
issue-only and explicit-Project connection plans SHALL retain their reviewed meaning.
Project completion SHALL NOT replace native issue state or specification/PR/CI gates.

#### Scenario: Issues-only selected
- **WHEN** the user selects issues-only with repository access but no Project permissions
- **THEN** setup plans a usable issue-only connection and reports the lack of native in-progress tracking
