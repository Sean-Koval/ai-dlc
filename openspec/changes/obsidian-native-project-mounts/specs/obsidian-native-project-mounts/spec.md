## ADDED Requirements

### Requirement: OM-01 Explicit local mounts
Vault linking SHALL retain portal default behavior and provide explicit mount mode exposing canonical docs and existing openspec directories as siblings beneath Projects/project. Bindings SHALL remain machine-local and use a stable checkout.

#### Scenario: Mount canonical sources
- **WHEN** the user selects mount mode for a stable checkout
- **THEN** preview lists exact links and apply exposes the original files without copying bodies; absent OpenSpec is reported without creating it

### Requirement: OM-02 Preservation and recovery
Mount setup SHALL be idempotent, preserve authored notes and portals, support explicit adoption of matching links, reject conflicts, loops, overlapping targets and unexpected nested traversal, and report retained partial output.

#### Scenario: Existing or conflicting link
- **WHEN** matching unmanaged links or conflicting destinations exist
- **THEN** matching links require explicit adoption and conflicts preserve existing content without replacement

### Requirement: OM-03 Independent knowledge boundaries
Private knowledge operations SHALL retain their existing filesystem boundary; native mounts SHALL not authorize generic symlink traversal, synchronization or publication.

#### Scenario: Personal notes beside project mounts
- **WHEN** a private-note operation targets a mounted document
- **THEN** it refuses external traversal while ordinary repository editing remains available

