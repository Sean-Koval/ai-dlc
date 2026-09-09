## ADDED Requirements

### Requirement: DK-01 Canonical documentation navigation
The optional organized documentation preset SHALL provide a project map of architecture, decisions, specifications, operations and reference, preserve existing layouts and files, and retain OpenSpec as the sole formal specification home. The legacy `5-pillar` name SHALL select the same preset without creating `docs/specs/` or invented system descriptions.

#### Scenario: Existing architecture and decisions
- **WHEN** a repository already has `docs/architecture.md` and `docs/decisions/`
- **THEN** setup links those canonical locations, creates only missing navigation, and does not create competing architecture or ADR folders

#### Scenario: Specifications have not been initialized
- **WHEN** organized documentation is added before OpenSpec initialization
- **THEN** navigation identifies the intended OpenSpec location without pretending specifications exist or creating them itself

### Requirement: DK-02 Shared preview and preservation
Documentation planning SHALL be part of the shared adoption service. Preview SHALL report document additions and optional vault portal content without mutation. Static conflicts SHALL refuse before writes. Publication SHALL exclusively create new files through no-follow directory access, preserve authored replacements, and retain and report partial output on unexpected failure without pathname cleanup.

#### Scenario: Adoption conflicts with an authored file
- **WHEN** adoption reports a conflict with docs and vault options selected
- **THEN** neither repository documents nor vault content is changed

#### Scenario: A destination appears after planning
- **WHEN** an authored file appears at a planned destination
- **THEN** publication refuses to replace it and reports retained output for inspection

#### Scenario: A document parent is a symlink
- **WHEN** a document destination traverses a symlink or special file
- **THEN** setup refuses before publication and preserves outside files

### Requirement: DK-03 Local project portals
Vault linking SHALL create a normal Markdown project portal containing canonical file links, not document copies or directory symlinks. Vault paths SHALL resolve from machine configuration or an explicit local argument and SHALL not enter tracked project files. Portal creation SHALL validate a single safe filename, refuse symlinked destinations and legacy project mounts, preserve authored content even with the legacy force flag, and allow repeated identical setup without replacing personal annotations.

#### Scenario: A project links to Obsidian
- **WHEN** a user links a project to an existing selected vault
- **THEN** a project note links to its repository documentation and intended OpenSpec location without copying their bodies or modifying repository gitignore

#### Scenario: Vault path or portal conflicts
- **WHEN** the vault is missing, the project name escapes its namespace, or existing portal content belongs to another source
- **THEN** preflight refuses without scaffolding project documents or changing existing notes

#### Scenario: A user has an old directory link
- **WHEN** a legacy symlink occupies the project name
- **THEN** linking requests manual inspection or a new portal name and does not remove or rewrite the link

### Requirement: DK-04 Private knowledge boundaries
Knowledge find, note and append SHALL retain the original private-vault filesystem boundary. The name `Projects` SHALL NOT authorize external reads or writes. Portal search SHALL discover the portal note without fetching its source links.

#### Scenario: An arbitrary project symlink is present
- **WHEN** a vault contains a directory symlink to repository or private external content
- **THEN** find ignores its content and note and append refuse traversal, including nested symlinks

### Requirement: DK-05 Explicit document lifecycle and provenance
An optional project catalog SHALL identify canonical document paths, stable IDs, categories, owners and lifecycle status, optional actual review dates and intervals, source URLs with retrieval dates and optional versions, and superseding document IDs. Repository docs, OpenSpec artifacts, private notes and existing shared team pages SHALL have distinct authority. Source references SHALL not authorize fetching, copying, synchronization or publication.

#### Scenario: A local summary derives from a team page
- **WHEN** a summary is catalogued
- **THEN** its source URL and retrieval date identify provenance and its owner is responsible for explicit refresh; private annotations are kept separate from publication

### Requirement: DK-06 Read-only document checks
CLI and MCP SHALL share a read-only local inspection service reporting malformed metadata, duplicate IDs/paths, absent documents, broken ordinary local Markdown links, uncatalogued Markdown, byte-identical content, missing owners, unknown or overdue review and absent replacement/source references. It SHALL NOT claim semantic freshness, validate remote sources, mirror OpenSpec lifecycle, or automatically consolidate/delete content. Strict CLI mode SHALL return nonzero when findings exist; default mode SHALL expose findings without adding a mandatory project gate.

#### Scenario: Review metadata is overdue
- **WHEN** the actual review date exceeds its declared interval
- **THEN** inspection reports review-overdue rather than asserting the document is wrong or updating its review date

#### Scenario: A new uncatalogued duplicate appears
- **WHEN** documentation includes an unlisted file with a byte-identical body
- **THEN** inspection reports both conditions for human or agent review without modifying either file

#### Scenario: Catalog input is malformed
- **WHEN** catalog TOML or entry fields are invalid
- **THEN** inspection reports structured findings without a traceback or external reads

### Requirement: DK-07 Portable upkeep guidance
Generated project guidance SHALL direct agents to find and update canonical documents before creating alternatives, preserve existing layouts, record ownership and provenance, review affected docs when code changes, and supersede rather than silently delete. Guidance SHALL retain independent tracker, specification and publication responsibilities. Documentation organization SHALL not install another tracker or Confluence connector.

#### Scenario: A harness proposes a new guide
- **WHEN** it consumes project documentation guidance
- **THEN** the instructions require checking the project map, catalog and relevant specification artifacts first and distinguish personal notes from a reviewed team document
