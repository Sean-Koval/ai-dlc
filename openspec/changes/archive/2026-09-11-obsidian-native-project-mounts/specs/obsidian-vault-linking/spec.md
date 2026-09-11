## MODIFIED Requirements

### Requirement: DK-03 Local project portals
By default, vault linking SHALL create a normal Markdown project portal containing canonical file links, not document copies or directory symlinks. Vault paths SHALL resolve from machine configuration or an explicit local argument and SHALL not enter tracked project files. Explicit mount mode MAY expose canonical directories under the native project mount requirements. Portal creation SHALL validate a single safe filename, refuse symlinked destinations and legacy project mounts, preserve authored content even with the legacy force flag, and allow repeated identical setup without replacing personal annotations.

#### Scenario: A project links to Obsidian
- **WHEN** a user links a project to an existing selected vault
- **THEN** a project note links to its repository documentation and intended OpenSpec location without copying their bodies or modifying repository gitignore

#### Scenario: Vault path or portal conflicts
- **WHEN** the vault is missing, the project name escapes its namespace, or existing portal content belongs to another source
- **THEN** preflight refuses without scaffolding project documents or changing existing notes

#### Scenario: A user has an old directory link
- **WHEN** a legacy symlink occupies the project name
- **THEN** linking requests manual inspection or a new portal name and does not remove or rewrite the link
