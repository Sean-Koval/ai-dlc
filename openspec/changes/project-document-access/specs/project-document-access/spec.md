## ADDED Requirements

### Requirement: PA-01 Scoped source access
CLI and MCP SHALL share project-document search and read operations scoped to the selected repository and declared document sources, returning canonical paths and source identity with bounded reads.

#### Scenario: Project and private content
- **WHEN** a query matches a declared repository document and an external private note
- **THEN** only eligible project content is returned with repository identity; symlink escape is refused

### Requirement: PA-02 Harness routing
Generated guidance SHALL distinguish project-document access from private knowledge and route edits through ordinary repository tools and verification, without following vault links as general authority.

#### Scenario: Harness chooses a tool
- **WHEN** a harness needs to inspect or edit a mounted project document
- **THEN** it discovers project operations and uses canonical repository paths rather than the private-note write API

