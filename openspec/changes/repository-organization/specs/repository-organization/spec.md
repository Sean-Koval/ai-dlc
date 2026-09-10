## ADDED Requirements

### Requirement: Canonical repository context
The system SHALL render a new or exact plain CLAUDE.md as only @AGENTS.md and a newline, accept it as ready, and preserve authored context in existing mixed files.

#### Scenario: Plain Claude reference
- **WHEN** an empty project or project with an exact plain reference is rendered repeatedly
- **THEN** CLAUDE.md remains the plain reference and readiness accepts it

### Requirement: Repository organization
AI-DLC SHALL keep formal changes in OpenSpec, clearly separate historical documents from current guidance, group internal Python modules by responsibility, and retain public command behavior.

#### Scenario: Cleanup does not change supported interfaces
- **WHEN** internal modules and historical documents are relocated
- **THEN** supported CLI, MCP and provider entry points continue to work and current references resolve

### Requirement: Prevent renewed layout drift
Required repository checks SHALL reject unapproved root Markdown, tool-specific scratch directories and ungrouped implementation modules.

#### Scenario: New root plan
- **WHEN** a root planning Markdown file is added
- **THEN** the layout check fails with its path and placement guidance
