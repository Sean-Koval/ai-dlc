## MODIFIED Requirements

### Requirement: TS-02 Role and tag selection
Sources SHALL select unannotated items for everyone and annotated items only when an item role or tag matches subscriptions. A machine binding MAY add personal roles but SHALL NOT add source definitions or replace provider roles. Selected skills, rules, supported hook features and MCP declarations SHALL render through owned project sections. When client skill destinations are rendered, each selected skill SHALL appear in shared guidance as a concise discovery entry and its complete body SHALL remain in each unique selected client skill destination. Complete selected rule bodies SHALL remain inline.

#### Scenario: A role matches a tagged skill
- **WHEN** an enrolled person's roles match a source skill's role metadata and supported clients are rendered
- **THEN** that skill appears as a discovery entry in AGENTS.md and as its complete unchanged content in selected client skill files; a person without a matching role or tag does not receive either

#### Scenario: A teamai layout is read
- **WHEN** the source declares layout = "teamai"
- **THEN** skills, rules, culture and safe MCP command declarations are imported with role/tag selection; hooks, agents and docs are ignored with a note, and env/ content is refused according to the security requirement

## ADDED Requirements

### Requirement: TS-05 Concise and usable skill discovery
Generated team skill discovery entries SHALL include the selected skill name, source ID, a bounded description and links to the complete SKILL.md files rendered for the effective clients. Entries SHALL NOT contain complete skill bodies when client destinations exist. Descriptions SHALL use nonempty string frontmatter descriptions when safely readable, normalize whitespace and control characters, and be at most 240 Unicode characters including an ellipsis for truncation. Otherwise entries SHALL use `Read the linked skill for its instructions.` as a fallback description. Description text SHALL be escaped as inert Markdown text. Discovery guidance SHALL tell the agent to read the linked file when a skill applies, without claiming native recognition.

#### Scenario: Each native destination is discoverable
- **WHEN** Codex, Claude Code and Antigravity are rendered in any supported combination
- **THEN** entries link only the effective render's destinations, using `.claude/skills/<name>/SKILL.md` for Claude Code and `.agents/skills/<name>/SKILL.md` for Codex and Antigravity, with shared destinations listed once and all targets resolving from the containing guidance file

#### Scenario: Antigravity reads its rule
- **WHEN** the generated team index appears in `.agents/rules/ai-dlc.md`
- **THEN** its links resolve to the same complete skill files as the root AGENTS.md index and native activation metadata outside the managed rule body survives

#### Scenario: Metadata requires fallback or escaping
- **WHEN** an otherwise valid native source skill has absent, malformed, non-string or empty description metadata, or a description contains multiline text, Markdown punctuation, HTML, controls or more than 240 characters
- **THEN** rendering uses the defined fallback or normalized bounded escaped description without adding active markup or changing the complete skill file, and does not introduce a new source validation rejection for optional descriptions

#### Scenario: Native discovery is unavailable
- **WHEN** an agent reads generated guidance but its native skill-discovery behavior is unavailable or unverified
- **THEN** the index provides a concrete file-reading instruction and usable paths for every selected skill, while readiness does not claim live native qualification

#### Scenario: No clients are selected
- **WHEN** the effective render client list is empty and selected team skills exist
- **THEN** complete skill bodies remain inline in shared guidance so all selected skills remain accessible without generating an unselected client's files

### Requirement: TS-06 Ownership-preserving compact guidance migration
The renderer SHALL migrate intact generated guidance to concise discovery using existing managed-section ownership and transactions. It SHALL preserve complete skill content, locked provenance, ownership schema, selection and explicit activation semantics. Dry-run rendering SHALL NOT write. Edited or authored conflicts SHALL refuse before any writes. Updating or removing a selected skill SHALL update its discovery entry and active files together within the existing render scope and recovery contract.

#### Scenario: Existing generated guidance upgrades
- **WHEN** an intact legacy section contains full selected skill bodies and ordinary rendering applies the compact representation
- **THEN** its skill entries become concise, full rules and exact skill-file bytes remain available, existing ownership provenance and authored surrounding text survive, and repeated rendering is clean

#### Scenario: Existing guidance or skill was edited
- **WHEN** managed guidance, a source-owned skill, or a destination's local ownership conflicts with the planned output
- **THEN** rendering refuses without changing guidance, skill files, ownership or source locks

#### Scenario: Selection changes and recovers
- **WHEN** a source skill is deselected, rendered, then selected again
- **THEN** the active discovery entry and in-scope exports are removed and restored together, retained backups follow the existing non-deleting recovery contract, and no authored file or backup is adopted

#### Scenario: Source revision advances
- **WHEN** a subscribed source changes its description and body after enrollment
- **THEN** rendered discovery and skill files remain bound to the active lock until successful explicit sync activation and a subsequent render, after which they reflect that same new locked source

#### Scenario: Explicit client render
- **WHEN** only one supported client is explicitly rendered
- **THEN** the current discovery entries reference the destinations that operation renders and unrelated client files retain the existing preservation behavior

### Requirement: TS-07 Measurable guidance size
Verification SHALL measure generated UTF-8 guidance bytes independently of complete skill-file bytes using deterministic fixtures. With skill metadata and rule bodies unchanged, increasing a selected skill's instruction body SHALL NOT increase concise guidance bytes when a native destination exists. Verification SHALL demonstrate a smaller concise representation than the legacy inline representation for a long-body fixture without asserting token, cost, latency or native-client qualification results.

#### Scenario: A selected skill becomes longer
- **WHEN** the same valid fixture skill is rendered with short and long instruction bodies while its name, source, description, clients and rules remain constant
- **THEN** generated guidance has the same byte count in both renders, each complete export matches its corresponding skill bytes, and the long-body compact guidance is smaller than that fixture's equivalent legacy inline guidance
