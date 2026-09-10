# obsidian-project-workspace Specification

## Purpose
Organize private project workspaces in Obsidian with canonical source links, personal note templates and additive setup that preserves authored content.
## Requirements
### Requirement: OW-01 Linked workspace navigation
Optional vault workspace setup SHALL provide Markdown project properties, note templates and optional native Bases views for active projects, questions and learnings. Project document bodies SHALL remain canonical in Git.

#### Scenario: Linked workspace navigation
- **WHEN** a developer opens the project workspace
- **THEN** canonical docs, personal notes and unresolved questions are discoverable through links

### Requirement: OW-02 Preserving workspace upgrades
Workspace additions and portal upgrades SHALL preview exact changes, preserve authored notes and annotations, and refuse conflicts or unsafe filesystem traversal. Machine bindings SHALL remain local with actionable missing-source diagnostics.

#### Scenario: Preserving workspace upgrades
- **WHEN** a portal contains personal annotations or a concurrent edit
- **THEN** upgrade preserves those bytes or refuses without overwriting

### Requirement: OW-03 Selective personal continuity
Daily workflow guidance SHALL retrieve project-relevant context and capture only selected personal learning, distinguish interpretations from sources, and avoid automatically summarizing all activity.

#### Scenario: Selective personal continuity
- **WHEN** a private learning is linked to a project
- **THEN** it remains local and is not treated as a publishable canonical specification
