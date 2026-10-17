## MODIFIED Requirements

### Requirement: PT-01 Explicit provider selection
Scaffolding and adoption SHALL accept supported provider selections independently of language preset and SHALL preserve legacy defaults when those selections are omitted.

#### Scenario: A personal project chooses Plane
- **WHEN** a user selects Plane tracking with the explicit unsupported-adapter opt-in and Obsidian knowledge
- **THEN** the preview selects those providers and their applicable setup/guidance without selecting another tracker
- **WHEN** the same selection omits the opt-in
- **THEN** scaffolding refuses before staging and names `--allow-unsupported`

#### Scenario: An existing caller omits provider options
- **WHEN** the legacy scaffold input is used
- **THEN** its prior provider defaults and applicable completion gates remain unchanged
