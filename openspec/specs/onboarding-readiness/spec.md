# onboarding-readiness Specification

## Purpose
Report truthful SCM and deployment readiness and guide private vault enrollment without equating local configuration with authentication or live qualification.
## Requirements
### Requirement: OR-01 Truthful SCM readiness
The standard GitHub SCM selection SHALL resolve its packaged guidance, existing git/gh executable requirements and root-level scm.repository configuration. Repository identity SHALL follow the runtime owner/repo syntax, and local prerequisites SHALL NOT claim authentication or live CI qualification.

#### Scenario: Provider-local repository cannot mask missing SCM identity
- **WHEN** providers.github.repository is populated but scm.repository is missing or malformed
- **THEN** readiness reports the required SCM configuration and stays not ready

#### Scenario: GitHub CLI is absent
- **WHEN** a valid SCM repository is configured but gh is unavailable
- **THEN** readiness reports a missing executable prerequisite without contacting GitHub

#### Scenario: A component override cannot conceal runtime incompatibility
- **WHEN** a provider borrows a trusted built-in component with an incompatible known runtime kind or an unknown runtime kind
- **THEN** readiness blocks the mismatch and retains the borrowed component's applicable root requirements

#### Scenario: Explicit extensions retain borrowed requirements
- **WHEN** an executable or Python extension selects a compatible built-in component
- **THEN** readiness applies that component's requirements without loading the extension or claiming runtime qualification

#### Scenario: Existing runtime aliases retain their metadata
- **WHEN** an existing Registry alias selects a component compatible with its canonical runtime role
- **THEN** readiness preserves applicable canonical and component requirements, while digest-verified custom component declarations remain metadata-only and unverified

### Requirement: OR-02 Explicit inactive deployment
The none deployment choice SHALL report inactive capability without requiring deployment tools or qualification. Unknown and incompatible provider selections SHALL remain blocked.

#### Scenario: A scaffold disables deployment
- **WHEN** deploy selects none
- **THEN** readiness describes disabled deployment rather than an unsupported or live-qualified adapter

#### Scenario: An active extension borrows inactive deployment guidance
- **WHEN** a runtime kind other than the inactive capability selects the none component
- **THEN** readiness blocks the mismatch and does not report inactive deployment

### Requirement: OR-03 Private vault enrollment guidance
The work-computer guide SHALL provide executable reviewed source/ref enrollment steps and identify the emitted machine configuration path for paths.vault. The route SHALL preserve project tracker/client choices and keep machine paths outside shared project files.

#### Scenario: A newly cloned installation binds an existing vault
- **WHEN** a user enrolls an explicitly reviewed profile and sets an existing vault in the resulting machine file
- **THEN** ordinary project readiness resolves that directory while authentication and native recognition remain unverified

