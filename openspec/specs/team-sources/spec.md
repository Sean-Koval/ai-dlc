# team-sources Specification

## Purpose
Distribute reviewed team guidance and safe client declarations through pinned
profile subscriptions, explicit activation and ownership-preserving rendering.
## Requirements
### Requirement: TS-01 Pinned and locked team sources
Personal schema 4 profiles SHALL accept additive source subscriptions with id, git, ref, roles, tags and optional layout. Enrollment SHALL lock exact source commits and content digests beside the profile commit. Rendering SHALL verify and use only locked content offline. Sync SHALL preview candidate changes and activate only after explicit apply succeeds.

#### Scenario: Source ref advances
- **WHEN** a local bare source ref moves after enrollment
- **THEN** rendered content remains unchanged until machine sync --apply and a subsequent render

#### Scenario: Session notices newer content
- **WHEN** a session starts and a subscribed remote ref has changed
- **THEN** the hook prints "team source <id> has a newer revision; run `ai-dlc machine sync`" without changing the lock, cache or rendered files

### Requirement: TS-02 Role and tag selection
Sources SHALL select unannotated items for everyone and annotated items only when an item role or tag matches subscriptions. A machine binding MAY add personal roles but SHALL NOT add source definitions or replace provider roles. Selected skills, rules, supported hook features and MCP declarations SHALL render through owned project sections.

#### Scenario: A role matches a tagged skill
- **WHEN** an enrolled person's roles match a source skill's role metadata
- **THEN** that skill appears in AGENTS.md and selected client skill files; a person without a matching role or tag does not receive it

#### Scenario: A teamai layout is read
- **WHEN** the source declares layout = "teamai"
- **THEN** skills, rules, culture and safe MCP command declarations are imported with role/tag selection; hooks, agents and docs are ignored with a note, and env/ content is refused according to the security requirement

### Requirement: TS-03 Collisions are refused
Rendering SHALL refuse source names that collide with shipped, bundled, local or other selected source skills, and conflicting MCP declarations, before modifying outputs. It SHALL preserve authored and edited owned files.

#### Scenario: An authored skill exists
- **WHEN** a selected source skill shares a name with an unowned local skill
- **THEN** rendering refuses without overwriting any output, even when their bytes match

### Requirement: TS-04 No secrets or executable content
Sources SHALL contain only regular bounded UTF-8 files without symlinks, executable files or env/ directories. Declarative configuration SHALL reject environment values and embedded credentials; diagnostics SHALL name the path without echoing secret values. Validation SHALL precede filtering and cache activation.

#### Scenario: Unsafe source contents
- **WHEN** either layout includes a symlink, executable or env/ file, or teamai MCP contains a token value
- **THEN** enrollment and sync refuse with a diagnostic naming the unsafe path and preserve the active lock
