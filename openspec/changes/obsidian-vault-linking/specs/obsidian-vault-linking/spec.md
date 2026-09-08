## Purpose

Provides native bidirectional linking between project documentation and an Obsidian vault, safe traversal of symlinked note trees during knowledge search operations, and support for the 5-pillar documentation architecture.

## ADDED Requirements

### Requirement: Symlink-safe note discovery in knowledge operations
The knowledge subsystem SHALL traverse directory symlinks within the configured Obsidian vault when scanning for notes, while strictly preventing traversal through symlinks that point outside authorized project doc directories or back above the vault root.

#### Scenario: Traversing symlinked project docs in vault
- **WHEN** an agent or user invokes knowledge find with a query matching content inside a symlinked project directory under `Projects/<name>/`
- **THEN** the system returns matching notes located within the symlink target.

#### Scenario: Preventing traversal through external arbitrary symlinks
- **WHEN** a symlink in the vault points outside recognized project documentation boundaries or attempts relative parent directory escapes
- **THEN** the knowledge scanner safely ignores the escaping link and reports an error or warning without crashing.

### Requirement: CLI Project Vault Linking
The CLI SHALL provide a `project link-vault` command that resolves the active machine's configured `paths.vault`, establishes a symlink from the target project's `docs/` folder into `<vault>/Projects/<project-name>`, and ensures git ignores Obsidian internal files.

#### Scenario: Linking project docs directory into configured vault
- **WHEN** user executes `ai-dlc project link-vault` inside a repository with an existing or new `docs/` directory
- **THEN** a symlink `<vault>/Projects/<project-name>` pointing to `<project-root>/docs` is created.

#### Scenario: Updating gitignore with Obsidian patterns
- **WHEN** `project link-vault` completes symlink creation
- **THEN** `.gitignore` in the project root is updated to include `.obsidian/` and `.trash/` if not already present.

#### Scenario: Reporting error when machine has no vault configured
- **WHEN** user executes `ai-dlc project link-vault` on an enrolled machine where `paths.vault` is not configured
- **THEN** the command exits with a non-zero code and instructs the user to configure `paths.vault` in their machine configuration.

### Requirement: 5-Pillar Documentation Preset Support
The project initialization and adoption commands SHALL support a `--docs-preset 5-pillar` option that scaffolds the five pillar directories (`architecture/`, `adr/`, `specs/`, `runbooks/`, `reference/`) and a Map of Content `docs/index.md`.

#### Scenario: Scaffolding 5-pillar structure on adopt or init
- **WHEN** a project is initialized or adopted with `--docs-preset 5-pillar`
- **THEN** the system generates the 5-pillar folder structure and an initial `docs/index.md` with Mermaid navigation.

#### Scenario: Preserving existing docs files during adoption
- **WHEN** a project with existing documentation is adopted with `--docs-preset 5-pillar`
- **THEN** existing documentation files are strictly preserved and never overwritten or deleted.
