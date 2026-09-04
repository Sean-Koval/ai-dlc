## Why

AI-DLC has sound configuration, setup, and rendering primitives, but a person
cannot yet enroll a new machine from one portable, reviewable source of personal
desired state. That leaves profile paths, machine-specific settings, and repeated
setup as manual knowledge rather than a safe lifecycle.

The approved [portable profile and machine enrollment design](../../../../docs/superpowers/specs/2026-09-03-portable-profile-enrollment-design.md)
defines the first dogfooding cycle that closes this gap without adding a hosted
control plane or bringing credentials into AI-DLC-managed files.

## What Changes

- Add a Git-backed, secret-free personal profile bundle with an identity and
  logical credential requirements.
- Enroll a profile at an exact Git commit, materialize a digest-verified local
  cache, and bind it to machine-local paths and credential environment names.
- Add preview-first machine enrollment, migration, planning, apply, sync, status,
  and doctor operations.
- Automatically resolve the enrolled personal and machine layers while preserving
  existing explicit overrides and schema-4 interfaces.
- Document a nonpersonal example, migration path, verification evidence, and
  remaining provider, cloud, and release qualification work.

## Capabilities

### New Capabilities

- `portable-profile-enrollment`: reproducible, secret-free personal profile
  enrollment and deliberate per-machine reconciliation.

## Impact

The Python CLI and shared services gain profile-source, enrollment, credential,
configuration, and machine lifecycle boundaries. Configuration and provisioning
tests must establish cache integrity, transactional active-state preservation,
two-machine portability, redaction, and compatibility. No runtime dependency,
hosted service, provider credential, or remote state change is introduced by this
change. Existing configuration, setup, profile, doctor, and explicit-file routes
remain compatible dependencies of the new enrollment capability rather than a
separately modified capability.
