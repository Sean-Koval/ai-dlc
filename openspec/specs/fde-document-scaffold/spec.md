# fde-document-scaffold Specification

## Purpose
TBD - created by archiving change fde-document-scaffold. Update Purpose after archive.
## Requirements
### Requirement: FDE-01 Complete local engagement hierarchy
Scaffolding SHALL create an engagement charter and seven ordered stage folders,
each with `_index.md`, initial lifecycle status and explicit exit criteria fields.

#### Scenario: New engagement
- **WHEN** a user scaffolds a valid new slug
- **THEN** the charter contains sponsor and business-goal sections and links to all seven stage pages with ACTIVE, GATED, GATED and four PLANNED initial states

### Requirement: FDE-02 Safe reviewed output
Scaffolding SHALL write only below the selected repository docs directory,
refuse unsafe paths and existing engagements, and support a write-free dry run.

#### Scenario: Existing engagement or escaped destination
- **WHEN** the target exists or a path includes traversal or a symlink
- **THEN** scaffolding refuses without replacing existing files

#### Scenario: Preview
- **WHEN** dry run is requested
- **THEN** exact prospective files and contents are returned without filesystem mutation

### Requirement: FDE-03 Explicit stage gates
Validation SHALL reject missing stage pages, malformed metadata, unsupported
statuses, exit completion without evidence and downstream activation or exit
completion before every preceding stage has satisfied its exit criteria.

#### Scenario: Premature design activation
- **WHEN** Design is ACTIVE while Discover or Frame lacks completed exit criteria
- **THEN** validation fails and names the prerequisite stages

#### Scenario: Reviewed progression
- **WHEN** each preceding stage records true exit completion with evidence
- **THEN** validation accepts activation of the next stage

### Requirement: FDE-04 Portable guidance and honest publication boundary
Scaffolding SHALL include agent guidance for stage conventions, validation and
selected shared documents, preserve the private-vault boundary, and never claim
to create remote pages. Explicit supplied space and parent hints SHALL be retained
without inventing descendant page identities.

#### Scenario: Confluence destination provided
- **WHEN** a scaffold names a space and parent
- **THEN** only the charter records that target hint, local output names publication unavailable, and no remote operation occurs

