## MODIFIED Requirements

### Requirement: RD-04 Actionable unavailable runtime
Project check SHALL resolve the configured runtime manager from PATH first and, when PATH lacks it, from the bootstrap bin directory the bootstrap installs into, honouring the same environment override diagnostics honour. A runtime found only in the bootstrap bin SHALL be used through the PATH of the environment the checks run in, SHALL be noted once on stderr together with the permanent activation remedy, and SHALL NOT change the check receipt or the process environment. Checks SHALL keep refusing to install tools. When neither location has the runtime, project check SHALL report the unavailable runtime as a structured failure with a nonzero exit, one concise message naming the missing executable and an ordered activation remedy, without a traceback. Machine-readable output SHALL remain valid, SHALL state that no check ran, and SHALL NOT present an empty or partial result as a passing run. No check receipt SHALL be written when no check ran.

#### Scenario: The selected runtime is only in the bootstrap bin
- **WHEN** PATH lacks the configured runtime manager and the bootstrap bin directory holds it as an executable regular file
- **THEN** required checks run through that runtime, the receipt is written with the same environment digest as a run whose PATH already selected it, one stderr line names the bootstrap directory and the permanent remedy, and no tool is installed

#### Scenario: The selected runtime is missing from PATH and the bootstrap bin
- **WHEN** neither PATH nor the bootstrap bin directory has the configured runtime manager and required checks are requested
- **THEN** the command exits nonzero with one concise message and a remedy that names workspace diagnostics, shell activation and rerunning the bootstrap, and prints no traceback

#### Scenario: A machine-readable caller observes the failure
- **WHEN** the same failure occurs with machine-readable output requested and a receipt path given
- **THEN** the output is valid and records that no check ran, and no receipt file is created
