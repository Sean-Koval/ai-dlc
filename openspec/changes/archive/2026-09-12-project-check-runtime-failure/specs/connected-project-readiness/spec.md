## ADDED Requirements

### Requirement: RD-04 Actionable unavailable runtime
Project check SHALL report an unavailable configured runtime as a structured failure with a nonzero exit, one concise message naming the missing executable and an ordered activation remedy, without a traceback. Machine-readable output SHALL remain valid, SHALL state that no check ran, and SHALL NOT present an empty or partial result as a passing run. No check receipt SHALL be written when no check ran.

#### Scenario: The selected runtime is missing from PATH
- **WHEN** the configured runtime manager is not on PATH and required checks are requested
- **THEN** the command exits nonzero with one concise message and a remedy that names workspace diagnostics, shell activation and rerunning the bootstrap, and prints no traceback

#### Scenario: A machine-readable caller observes the failure
- **WHEN** the same failure occurs with machine-readable output requested and a receipt path given
- **THEN** the output is valid and records that no check ran, and no receipt file is created
