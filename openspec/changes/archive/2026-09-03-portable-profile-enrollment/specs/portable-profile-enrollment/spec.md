## ADDED Requirements

### Requirement: Enroll a secret-free pinned personal profile

The system SHALL resolve a personal profile from a Git source to an exact commit,
validate its declared identity and secret-free content, and preview enrollment by
default. It SHALL activate a machine-local enrollment lock only when explicitly
applied.

#### Scenario: Profile identity is enrolled deliberately

- **WHEN** an operator enrolls a profile whose declared ID matches `--profile-id`
- **THEN** the preview reports the requested ref, resolved commit, content digest,
  proposed lock, required bindings, and missing credential variable names without
  exposing credential values

#### Scenario: Invalid candidate preserves active state

- **WHEN** source resolution, validation, or reconciliation of a candidate fails
- **THEN** the current active enrollment lock remains unchanged

### Requirement: Separate portable and machine-local configuration

The system SHALL resolve configuration in base, personal, project, then machine
order. A profile supplies portable preferences and logical credential requirements;
a machine binding supplies only its local paths and credential environment-variable
names.

#### Scenario: Two machines use one pinned profile

- **WHEN** two isolated machines enroll the same resolved profile commit
- **THEN** they resolve the same portable desired state while retaining distinct
  machine bindings and credential variable names

#### Scenario: Explicit paths retain their scope

- **WHEN** an operator supplies an explicit personal or machine configuration file
- **THEN** it replaces the enrolled file only in that matching scope and does not
  become a new precedence layer

### Requirement: Synchronize and operate safely from verified cache

The system SHALL materialize only the declared profile file into a
digest-verified local cache. Synchronization SHALL preview a moved source ref and
require explicit apply before changing the active lock.

#### Scenario: Offline operation uses verified cache

- **WHEN** the source is unavailable and the active cached profile passes
  integrity validation
- **THEN** status and planning use that active cached revision without fetching

#### Scenario: Sync is transactional

- **WHEN** synchronization is applied to a new verified commit
- **THEN** reconciliation completes before the new lock is atomically activated

### Requirement: Preserve credential and interface compatibility boundaries

The system SHALL not persist, return, log, or render credential values. It SHALL
retain schema-4 configuration compatibility and existing setup, profile, doctor,
and explicit machine interfaces while adding the machine lifecycle.

#### Scenario: Credential readiness is redacted

- **WHEN** status, planning, or doctor evaluates a credential requirement
- **THEN** it reports only the logical ID, environment variable name, and presence
  state, never the environment value

#### Scenario: Existing explicit workflow remains available

- **WHEN** an operator uses an existing setup, profile, doctor, or explicit
  `--machine` entry point
- **THEN** it continues to resolve through the compatible configuration and
  reconciliation boundaries
