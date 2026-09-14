## MODIFIED Requirements

### Requirement: TR-01 Explicit traceability

New delivery guidance SHALL map product requirement IDs to formal behavioral scenarios when needed, a deliverable work item, and verification. Scope, rationale, spec, and task list SHALL retain distinct ownership. `work new` SHALL create a schema-valid unreviewed record from explicit fields or a configured tracker item without publication or mutation state. Existing records and unsafe IDs SHALL be refused without writing. Missing tracker content SHALL remain explicit TODO placeholders.

#### Scenario: A feature is decomposed
- **WHEN** one outcome needs independently releasable behavior changes
- **THEN** each ticket has explicit requirement references, dependencies, exclusions, and acceptance while each required OpenSpec change can finish independently

#### Scenario: A record is created from a tracker item
- **WHEN** an issue has an Acceptance or Acceptance criteria section with bullet lines
- **THEN** the new record carries those acceptance lines, its tracker reference and reviewed=false

#### Scenario: Missing issue content remains explicit
- **WHEN** an issue has no acceptance section
- **THEN** acceptance contains TODO: state acceptance and no content is invented

#### Scenario: Offline drafting
- **WHEN** explicit title, scope and acceptance are supplied without an issue
- **THEN** creation and validation need no provider call or state directory
