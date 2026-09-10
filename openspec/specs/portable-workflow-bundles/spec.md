# portable-workflow-bundles Specification

## Purpose
Import pinned workflow assets with complete provenance and integrity, preserve owned rendering boundaries and enable direct use and verified offline continuation.
## Requirements
### Requirement: WB-01 Pinned portable workflow assets

Imported workflow bundles SHALL record source, exact resolved revision, and complete file digests; preview SHALL leave active project and client files unchanged.

#### Scenario: A source ref moves before apply
- **WHEN** apply resolves different content from the previewed revision
- **THEN** the import requires a fresh preview and does not activate changed content

#### Scenario: A reviewer previews an import
- **WHEN** a portable Git source, exact advertised ref, requested bundle ID, manifest, and payload are valid
- **THEN** preview reports the exact commit, manifest digest, export mappings, payload paths and hashes without changing project, client, profile, or remote state

#### Scenario: Bundle metadata or content is unsafe
- **WHEN** JSON has duplicate keys, the manifest ID differs from the requested ID, a path/type/size/count/digest rule fails, a payload is not exactly one declared export, or the checkout contains undeclared payload
- **THEN** validation fails before any project or client write

#### Scenario: A declared skill is not portable harness guidance
- **WHEN** its exact four-line `name`/`description` frontmatter is missing or malformed, the name differs from its export, the description violates its bounds, or its Markdown body is empty
- **THEN** validation rejects the bundle before import or rendering

#### Scenario: Source provenance is machine-specific
- **WHEN** an import source is a local path or `file:` URL
- **THEN** import refuses it so committed provenance cannot contain a machine-specific source

#### Scenario: Apply publishes a complete vendored bundle
- **WHEN** the freshly resolved commit equals the required preview commit and all bytes still validate
- **THEN** apply transactionally vendors the manifest, every declared payload, and a deterministic lock authenticating the manifest and complete payload map without selecting or rendering the bundle

#### Scenario: Staged or installed content changes during publication
- **WHEN** a first import or update encounters changed manifest, lock, payload, tree entries, or directory identity after staging or installation
- **THEN** apply raises an error instead of reporting success, preserves the changed occupants without recursive deletion, restores the previous active bundle where safe, and reports retained paths for inspection

### Requirement: WB-02 Owned rendering and integrity

Bundle validation SHALL reject unsafe, undeclared, tampered, or colliding assets before rendering; owned updates SHALL preserve authored modifications.

#### Scenario: An imported skill has a local edit
- **WHEN** a later render after importing an updated revision would overwrite that edit
- **THEN** the existing ownership workflow reports the conflict and preserves the edited file

#### Scenario: A selected export collides
- **WHEN** selected bundles reuse an export name, a bundle skill reuses a shipped skill name, or any bundle destination already exists without matching bundle ownership
- **THEN** rendering reports the collisions before writes and preserves every existing file

#### Scenario: The same owner has an intact update
- **WHEN** a newly imported revision changes an output whose current bytes still match that bundle's recorded ownership
- **THEN** rendering may update the owned output and its digest without changing authored files

#### Scenario: A selected bundle removes an export
- **WHEN** an updated selected bundle no longer exports a previously bundle-owned path
- **THEN** rendering removes the obsolete output only when its current digest is intact and otherwise blocks without writes

#### Scenario: Bundle publication fails
- **WHEN** an operational failure occurs while replacing a vendored tree or during a render involving selected or previously owned bundle outputs, and concurrent writes do not prevent safe restoration
- **THEN** the previous vendored tree and every file in the complete render transaction are restored byte for byte

#### Scenario: Import backup or stage cleanup could delete authored content
- **WHEN** an import has retained an old bundle backup, an unused or partial stage, or content displaced during recovery
- **THEN** it does not recursively delete or rewrite those occupants, reports sorted project-relative `retained_paths` on returned results or retained-path notes on errors, and leaves them outside active bundle ownership

#### Scenario: An authored destination prevents import recovery
- **WHEN** a concurrent destination or unavailable rename prevents restoring the previous active bundle
- **THEN** recovery refuses to overwrite that destination, preserves available old and staged content, and reports the incomplete restoration and relevant paths on the error

#### Scenario: An import backup changes before or during restoration
- **WHEN** the backup's saved directory identity or previous bytes differ before restoration, or authentication detects a change after the restore move
- **THEN** recovery does not move a known mismatched source, verifies any attempted restore against the saved identity and bytes, and reports incomplete recovery with all known affected names on mismatch without deleting occupants or claiming the old tree was restored

#### Scenario: A later import encounters retained residue
- **WHEN** previous imports left backups or stages outside the active bundle directory
- **THEN** preview and apply neither adopt nor modify that residue, later updates use distinct backup names, and results with no newly retained paths omit `retained_paths`

#### Scenario: Render stage cleanup could delete authored content
- **WHEN** a render fails after creating a complete or partial temporary stage, including a stage displaced during rollback
- **THEN** recovery preserves the stage pathname without deleting or rewriting its occupant, restores transaction destinations where safe, and reports retained stage filenames or paths on the original failure for inspection

#### Scenario: Successful render backup cleanup could delete authored content
- **WHEN** a successful bundle render has moved an existing output to a backup pathname, including an obsolete output removed from active guidance
- **THEN** it retains that pathname without deleting or rewriting its occupant and reports sorted project-relative `retained_backups` paths in the render result for inspection

#### Scenario: A later render encounters retained backups
- **WHEN** previous successful renders have left backup files, including files edited after retention
- **THEN** preview and apply leave those files unchanged, do not adopt them into managed ownership, and do not treat them as active guidance; a result with no newly retained backups omits `retained_backups`

### Requirement: WB-03 Direct use and offline continuation

Selected vendored guidance SHALL be discoverable in supported harnesses and usable offline; instructions SHALL NOT depend on an AI-DLC daemon or prior chat.

#### Scenario: A fresh checkout has no network
- **WHEN** the committed bundle and lock are valid
- **THEN** the harness can discover the selected guidance from the checkout without contacting its source

#### Scenario: A project selects a bundle
- **WHEN** a unique bundle-ID slug is configured in project-level `agents.bundles` and its vendored content is valid
- **THEN** rendering exposes its skills in each selected supported client's native skill directory, exposes templates at `docs/templates/NAME.md`, and links both from managed project guidance

#### Scenario: One client is rendered
- **WHEN** a project with bundle outputs owned for multiple clients renders one selected client
- **THEN** outputs and ownership for every non-target client are preserved unchanged

#### Scenario: A non-project layer selects a bundle
- **WHEN** base, personal, or machine configuration defines `agents.bundles`
- **THEN** configuration validation rejects that layer without changing the active project

#### Scenario: Selected guidance is not usable
- **WHEN** a selected bundle is missing, tampered, invalid, colliding, locally edited, or not rendered
- **THEN** project readiness reports an actionable missing or blocked guidance check and does not report ready

