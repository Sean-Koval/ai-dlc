## ADDED Requirements

### Requirement: WB-01 Pinned portable workflow assets

Imported workflow bundles SHALL record source, exact resolved revision, and complete file digests; preview SHALL leave active project and client files unchanged.

#### Scenario: A source ref moves before apply
- **WHEN** apply resolves different content from the previewed revision
- **THEN** the import requires a fresh preview and does not activate changed content

### Requirement: WB-02 Owned rendering and integrity

Bundle validation SHALL reject unsafe, undeclared, tampered, or colliding assets before rendering; owned updates SHALL preserve authored modifications.

#### Scenario: An imported skill has a local edit
- **WHEN** a later import would overwrite that edit
- **THEN** the existing ownership workflow reports the conflict and preserves the edited file

### Requirement: WB-03 Direct use and offline continuation

Selected vendored guidance SHALL be discoverable in supported harnesses and usable offline; instructions SHALL NOT depend on an AI-DLC daemon or prior chat.

#### Scenario: A fresh checkout has no network
- **WHEN** the committed bundle and lock are valid
- **THEN** the harness can discover the selected guidance from the checkout without contacting its source
