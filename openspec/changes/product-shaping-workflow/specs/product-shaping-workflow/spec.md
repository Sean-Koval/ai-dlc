## ADDED Requirements

### Requirement: PS-01 Evidence-based product shaping

The workflow SHALL distinguish observed evidence, user decisions, and hypotheses; it SHALL compare feasible options and identify a bounded outcome before proposing implementation.

#### Scenario: A request contains only a feature idea
- **WHEN** a user asks for a dashboard without explaining the underlying problem
- **THEN** the agent investigates audience and task evidence and records assumptions instead of treating the requested layout as validated product direction

### Requirement: PS-02 Separate greenfield and brownfield entry paths

Greenfield guidance SHALL shape the smallest useful outcome; brownfield guidance SHALL inspect existing behavior and preserve explicit compatibility boundaries.

#### Scenario: An existing workflow is changed
- **WHEN** a product already has users and integrations
- **THEN** the brief identifies current behavior, affected consumers, migration/recovery needs, and a bounded change

### Requirement: PS-03 Proportional handoff

The workflow SHALL produce traceable outcome/requirement IDs and an explicit proceed, investigate, or stop decision; material unknowns SHALL remain visible and SHALL NOT become invented acceptance facts.

#### Scenario: Evidence is insufficient
- **WHEN** the value of a proposed feature remains uncertain
- **THEN** the next slice is a bounded investigation with its evidence goal rather than an implementation commitment
