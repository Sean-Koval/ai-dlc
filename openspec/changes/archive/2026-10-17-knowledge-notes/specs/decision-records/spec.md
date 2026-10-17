## ADDED Requirements

### Requirement: DR-01 Projects start with the decision convention
`ai-dlc project init` SHALL produce `docs/decisions/README.md` describing `NNNN-slug.md` numbering, knowledge-note frontmatter, the supersede-not-edit rule, `checks:` in flightdeck's `flightdeck.spec/v1` grammar and CODEOWNERS guidance for the two-person rule, and `docs/templates/adr.md` with knowledge-note frontmatter (`kind: decision`, `status: proposed`) and the sections Context, Options considered, Decision, Consequences and Links.

#### Scenario: A new project is initialized
- **WHEN** `ai-dlc project init` creates a project
- **THEN** the decisions README and the ADR template exist with that content

### Requirement: DR-02 Decision frontmatter is validated
`ai-dlc docs check` SHALL validate the frontmatter of every `docs/decisions/*.md` record that has frontmatter against the knowledge-note schema, requiring `kind: decision` and `status`, and SHALL exit with status 2 on a schema error. Records without frontmatter SHALL be reported as information, not errors.

#### Scenario: A record lacks status
- **WHEN** a decision record's frontmatter has no `status`
- **THEN** `docs check` reports a schema error and exits 2

#### Scenario: An older record has no frontmatter
- **WHEN** a record has no frontmatter
- **THEN** `docs check` reports it as information and does not fail on it

### Requirement: DR-04 Checks are shape-checked, never evaluated
Each `checks` entry SHALL be a `flightdeck.spec/v1` spec without its header: an `id` unique within the record and an `assert` holding exactly one operator, with optional `scope` (`turn`, `job`, `session`) and `severity` (`warn`, `fail`). `docs check` SHALL report shape errors and SHALL NOT evaluate any check.

#### Scenario: A check lacks its assertion
- **WHEN** a `checks` entry has no `assert`
- **THEN** `docs check` reports a schema error for that entry

#### Scenario: Two checks share an id
- **WHEN** two entries in one record have the same `id`
- **THEN** `docs check` reports that check ids must be unique

### Requirement: DR-03 Accepted decisions are superseded, not edited
When the committed version of a decision record has frontmatter with `status: accepted`, `docs check` SHALL fail with "accepted decisions are superseded, not edited" if the working-tree body differs from the committed body, unless the record's status is now `superseded`. A superseded record SHALL have `valid_to`. Frontmatter-only edits SHALL be allowed.

#### Scenario: An accepted body is edited
- **WHEN** the body of an accepted record differs from its committed version and its status is still `accepted`
- **THEN** `docs check` fails with "accepted decisions are superseded, not edited"

#### Scenario: The record is superseded
- **WHEN** the same edit sets `status: superseded` with a `valid_to` date
- **THEN** `docs check` reports no decision error
