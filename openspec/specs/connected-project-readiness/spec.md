# connected-project-readiness Specification

## Purpose
TBD - created by archiving change connected-project-readiness. Update Purpose after archive.
## Requirements
### Requirement: RD-01 Connected provisioning plan

Root-aware setup SHALL resolve explicit project and profile selections into required tool modules and guidance, preserving existing no-root command behavior and authored files.

#### Scenario: A project requires an absent tool
- **WHEN** the personal profile omits the OpenSpec installation module while the project explicitly selects OpenSpec
- **THEN** the root-aware plan includes that module with its provider-selection reason and applies nothing until setup apply is invoked

### Requirement: RD-02 Readiness is actionable and scoped

Project readiness SHALL separately identify tool, configuration, credential, and guidance failures with next actions; it SHALL inspect only credential presence and SHALL NOT read secret files automatically.

#### Scenario: Tool installation alone is insufficient
- **WHEN** OpenSpec is executable but its selected harness guidance is missing
- **THEN** readiness reports the guidance gap and does not declare the project ready

### Requirement: RD-03 Environment consistency preserves local identity

Equivalent profile/project revisions SHALL resolve equivalent portable requirements with independent local bindings; unsupported capabilities SHALL be explicit.

#### Scenario: A second environment is headless
- **WHEN** a selected optional component requires a desktop while the target is headless
- **THEN** the report names the unsupported capability without substituting another provider or claiming full target qualification
