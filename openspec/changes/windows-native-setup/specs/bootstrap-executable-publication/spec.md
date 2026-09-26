## MODIFIED Requirements

### Requirement: BP-01 Complete executable publication
Bootstrap SHALL prepare executable bytes and permissions on the destination filesystem before replacing an owned installed executable, without modifying the previously installed object. Native Windows sharing restrictions SHALL cause a visible, recoverable refusal preserving the previous executable rather than an unlink-and-copy replacement.

#### Scenario: Another process retains the previous executable
- **WHEN** bootstrap publishes uv, uvx or mise while a reader has the old executable open on a platform and with sharing semantics that permit replacement
- **THEN** the installed path exposes the complete executable with executable permissions and the old reader retains its original bytes and open object identity (including the existing Unix inode behavior)

#### Scenario: Staging or publication fails
- **WHEN** copy, permission preparation or replacement fails before publication
- **THEN** bootstrap fails visibly and the previous installed executable remains unchanged

#### Scenario: Native sharing rules deny replacement
- **WHEN** Windows refuses publication because the old executable is open without compatible sharing
- **THEN** bootstrap reports the blocked replacement and preserves the previous installed bytes and selected executable
- **AND** retry after the handle is released can publish the fully prepared replacement
