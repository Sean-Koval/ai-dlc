# connected-project-readiness Specification

## Purpose
Plan project-aware provisioning and report actionable scoped readiness while preserving machine-local identity and existing setup behavior.
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

### Requirement: RD-04 Actionable unavailable runtime
Project check SHALL report an unavailable configured runtime as a structured failure with a nonzero exit, one concise message naming the missing executable and an ordered activation remedy, without a traceback. Machine-readable output SHALL remain valid, SHALL state that no check ran, and SHALL NOT present an empty or partial result as a passing run. No check receipt SHALL be written when no check ran.

#### Scenario: The selected runtime is missing from PATH
- **WHEN** the configured runtime manager is not on PATH and required checks are requested
- **THEN** the command exits nonzero with one concise message and a remedy that names workspace diagnostics, shell activation and rerunning the bootstrap, and prints no traceback

#### Scenario: A machine-readable caller observes the failure
- **WHEN** the same failure occurs with machine-readable output requested and a receipt path given
- **THEN** the output is valid and records that no check ran, and no receipt file is created

