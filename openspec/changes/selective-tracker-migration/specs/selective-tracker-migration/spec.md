## ADDED Requirements

### Requirement: TM-01 Defaults preserve retained work
A default-only tracker switch SHALL freeze retained effective bindings and references before changing the default, without migrating remote issues or modifying unrelated providers.

#### Scenario: A legacy record has no explicit tracker binding
- **WHEN** the project changes its tracker default for future work
- **THEN** the legacy record remains attached to its previously effective tracker and new records use the selected default

### Requirement: TM-02 Explicit selected mappings
Selected migration SHALL change only explicitly selected work and SHALL verify each target's account, project and reference before local apply.

#### Scenario: Only active work is selected
- **WHEN** a reviewed plan migrates a subset of retained work IDs
- **THEN** unselected records and all non-tracker references remain byte-for-byte unchanged

#### Scenario: A target mapping is unavailable or outside the selected project
- **WHEN** target verification fails or a selected record lacks a complete mapping
- **THEN** local migration refuses without changing bindings

### Requirement: TM-03 Resumable creation and provenance
Optional destination creation SHALL require a reviewed explicit plan, reconcile uncertain writes, and preserve durable source-to-target provenance without pretending remote and local mutation is atomic.

#### Scenario: Target creation succeeds before a local conflict
- **WHEN** a target exists but local apply fails its freshness check
- **THEN** old bindings remain in force, the created target is reported and retained, and retry reuses it instead of creating a duplicate

### Requirement: TM-04 Honest unavailable-source migration
An unavailable source provider SHALL not block local preview, but its missing state or history SHALL remain explicitly unknown and SHALL not be fabricated.

#### Scenario: Linear access is unavailable
- **WHEN** a user reviews migration based on local work records and verified target mappings
- **THEN** the plan identifies omitted remote-only information and applies only the explicitly reviewed mappings without claiming a complete import

### Requirement: TM-05 Gates and drift remain authoritative
Migration SHALL preserve existing completion policy and refuse stale configuration, changed work, changed target identities, or unexpected provider-binding drift.

#### Scenario: A target is already closed
- **WHEN** work is rebound to that issue
- **THEN** the rebind itself does not finish work or waive specification, merged-revision or CI gates

### Requirement: TM-06 Interchangeable supported destinations
Migration SHALL accept either GitHub Issues or Plane through the same target-verification and recovery service, without assuming Plane as the personal destination or coupling tracker choice to the SCM provider.

#### Scenario: The personal tracker choice changes
- **WHEN** a reviewed migration selects Linear to GitHub Issues, Linear to Plane, or a switch between GitHub Issues and Plane
- **THEN** the same selection, provenance, uncertainty and gate-preservation rules apply, unsupported state mappings are reported, and original state evidence is retained
