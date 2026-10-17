## MODIFIED Requirements

### Requirement: TM-04 Honest unavailable-source migration
An unavailable source provider SHALL not block local preview, but its missing state or history SHALL remain explicitly unknown and SHALL not be fabricated.

#### Scenario: Source tracker access is unavailable
- **WHEN** a user reviews migration based on local work records and verified target mappings
- **THEN** the plan identifies omitted remote-only information and applies only the explicitly reviewed mappings without claiming a complete import

### Requirement: TM-06 Interchangeable supported destinations
Migration SHALL accept either GitHub Issues or Plane through the same target-verification and recovery service, without assuming Plane as the personal destination or coupling tracker choice to the SCM provider.

#### Scenario: The personal tracker choice changes
- **WHEN** a reviewed migration moves retained work from another tracker to GitHub Issues or Plane, or switches between GitHub Issues and Plane
- **THEN** the same selection, provenance, uncertainty and gate-preservation rules apply, unsupported state mappings are reported, and original state evidence is retained

#### Scenario: Existing targets have cancelled or unknown state
- **WHEN** a reviewed existing-target mapping reads a cancelled or unknown logical state
- **THEN** the plan records it without changing remote state or treating it as completed work, identifies unknown source state and unsupported target transitions, and preserves completion gates

#### Scenario: Legacy saved mappings remain usable
- **WHEN** a valid schema1 saved plan is applied or its local receipt inspected
- **THEN** its original exact validation and bounded recovery rules remain available without fabricated new evidence
