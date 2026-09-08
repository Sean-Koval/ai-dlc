## ADDED Requirements

### Requirement: BP-01 Complete executable publication
Bootstrap SHALL prepare executable bytes and permissions on the destination filesystem before replacing an owned installed executable, without modifying the previously installed object.

#### Scenario: Another process retains the previous executable
- **WHEN** bootstrap publishes uv, uvx or mise while a reader has the old executable open
- **THEN** the installed path exposes the complete executable with executable permissions and the old reader retains its original bytes and inode

#### Scenario: Staging or publication fails
- **WHEN** copy, permission preparation or replacement fails before publication
- **THEN** bootstrap fails visibly and the previous installed executable remains unchanged

### Requirement: BP-02 Independent download staging
Each download invocation SHALL use an independent temporary file, verify its configured digest before publication, and refuse invalid content without replacing an existing verified download.

#### Scenario: Two downloads overlap
- **WHEN** two invocations target the same cache destination
- **THEN** each invocation verifies its own bytes and cannot consume or remove the other invocation's staging file

### Requirement: BP-03 Non-deleting stage retention and bounded claims
Bootstrap SHALL retain and report unused or failed staging paths without pathname cleanup that could delete a replacement occupant. Source and scaffold scripts SHALL remain equivalent.

#### Scenario: A failed stage is replaced with authored content
- **WHEN** a staging operation fails after an external writer replaces its pathname
- **THEN** bootstrap preserves that occupant and reports the known staging path for inspection

#### Scenario: Publication fixtures pass
- **WHEN** local filesystem tests verify publication behavior
- **THEN** evidence distinguishes those checks from actual host startup qualification, shared environment serialization, cross-version toolset consistency and release qualification
