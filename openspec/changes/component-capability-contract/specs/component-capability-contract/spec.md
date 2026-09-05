## ADDED Requirements

### Requirement: CC-01 Deterministic capability resolution

The resolver SHALL produce stable component requirements for each explicitly selected role, deduplicate installation modules, and report an unresolved provider without silently selecting another provider.

#### Scenario: OpenSpec is selected without its module
- **WHEN** a project selects the OpenSpec provider but its personal module list contains only core and python
- **THEN** resolution identifies openspec as a required module and includes the provider guidance references

### Requirement: CC-02 Verified extension metadata

Custom component metadata SHALL be repository-relative, digest-verified, schema-validated data. It SHALL refer to existing installation recipes and SHALL NOT authorize executable commands.

#### Scenario: Custom metadata is altered
- **WHEN** the manifest bytes differ from the configured SHA-256
- **THEN** resolution fails before loading guidance or planning installations

### Requirement: CC-03 Compatibility and provenance

Existing schema-4 configurations SHALL remain valid; component metadata SHALL NOT weaken project checks or silently rebind active work.

#### Scenario: An alternative tracker is selected
- **WHEN** new work selects a registered executable provider and a matching component manifest
- **THEN** the stable tracker responsibility resolves through the declared component while previously bound work retains its existing provider
