# product-shaping-workflow Specification

## Purpose
TBD - created by archiving change product-shaping-workflow. Update Purpose after archive.
## Requirements
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

#### Scenario: Requirements contradict an existing compatibility boundary
- **WHEN** a requested default format change conflicts with explicit preservation of the existing default bytes
- **THEN** the agent records the contradiction and a bounded clarification, preserves the known consumer contract, and presents an opt-in alternative only as a proposal until decided

#### Scenario: A bounded non-UI increment is authorized
- **WHEN** the user has reviewed an opt-in increment, evidence supports its outcome, and material compatibility constraints are resolved
- **THEN** the agent recommends proceed to the specification decision and configured formal provider with stable brief IDs, without requiring a UI exercise or duplicate PRD

#### Scenario: The request is explicitly declined
- **WHEN** an incoming idea duplicates tracked work and the responsible user declines it as outside the current audience
- **THEN** the agent records stop with the reason and existing reference without republishing the item or inventing a ticket identifier

#### Scenario: Evidence is insufficient
- **WHEN** the value of a proposed feature remains uncertain
- **THEN** the next slice is a bounded investigation with its evidence goal rather than an implementation commitment

