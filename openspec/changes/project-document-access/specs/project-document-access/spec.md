## ADDED Requirements

### Requirement: PA-01 Scoped source access
CLI and MCP SHALL share project-document search and read operations scoped to the selected repository and declared document sources, returning canonical paths and source identity with bounded reads. Default eligibility SHALL include inventory-eligible Markdown beneath docs/ and openspec/. Additional sources SHALL be unique exact inventory-eligible repository-relative Markdown paths declared explicitly for the current call, with no persistent configuration or catalog schema change. Operations SHALL enforce the documented byte and result bounds, expose omissions and revalidate filesystem access without following symlinks.

#### Scenario: Default project sources
- **WHEN** a repository contains matching docs, OpenSpec, root and legacy Markdown
- **THEN** default search/read eligibility includes only inventory-eligible docs and OpenSpec files, does not open root or legacy bodies, and requires no catalog

#### Scenario: Explicit additional document
- **WHEN** the caller declares README.md through a repeated CLI source argument or the MCP sources list
- **THEN** that exact inventory-eligible file is added to the default scope for that call, with declared-source identity and no configuration write

#### Scenario: Reading does not implicitly expand scope
- **WHEN** the caller requests a root or legacy document without declaring it
- **THEN** the read is refused before opening its body, even though inventory can list the path

#### Scenario: Invalid declarations
- **WHEN** declarations contain more than 32 entries, duplicates, absolute paths, traversal, globs, directories, ignored or unavailable files, or symlinks
- **THEN** the operation rejects the declaration before any document-body reads and preserves the filesystem

#### Scenario: Bounded search includes nonmatches
- **WHEN** a literal case-insensitive search examines multiple documents
- **THEN** all examined body bytes including nonmatches consume one positive bounded budget, eligible paths are visited deterministically, and oversized bodies are omitted without being read

#### Scenario: Partial search remains explicit
- **WHEN** the byte budget or result limit prevents exhaustive examination, or a source cannot be read or decoded safely
- **THEN** the result identifies omitted and unexamined material with reasons and does not claim complete coverage or an authoritative absence of matches

#### Scenario: Bounded read and identity
- **WHEN** an eligible file fits the selected read budget
- **THEN** read returns its complete body, content digest, inclusive line range, canonical absolute path, repository-relative path and project-source identity; an oversized file instead has an explicit omission without a body read

#### Scenario: Invalid limits
- **WHEN** a caller supplies an empty search query, a byte budget outside 1 through 1048576, a result limit outside 1 through 100, or boolean/noninteger numeric limits
- **THEN** the operation rejects the request before document-body reads

#### Scenario: Equivalent CLI and MCP requests
- **WHEN** CLI and MCP issue equivalent requests against the same repository and source bytes
- **THEN** they expose equivalent scope, identities, content evidence, matches and omission metadata through the shared service

#### Scenario: Project and private content
- **WHEN** a query matches an eligible repository document and an external private note, including one reachable through a vault or source symlink
- **THEN** only eligible project content is returned, no private body is read, and symlink escape is refused

#### Scenario: Source changes after discovery
- **WHEN** a selected file or parent directory is replaced by a symlink or special file after inventory
- **THEN** the actual read refuses unsafe traversal or file access and reports the unavailable source rather than returning outside content

#### Scenario: Missing default directories
- **WHEN** docs or openspec is absent
- **THEN** the operation reports that source as unavailable without creating it and may inspect other eligible sources

### Requirement: PA-02 Harness routing
Generated guidance SHALL distinguish project-document access from private knowledge and route edits through ordinary repository tools and verification, without following vault links as general authority. Canonical and portable tool maps SHALL expose the new search/read operations and their explicit-source and omission semantics.

#### Scenario: Harness chooses a tool
- **WHEN** a harness needs to inspect or edit a mounted project document
- **THEN** it discovers project operations and uses returned canonical repository paths for ordinary edits and Git verification rather than the private-note write API

#### Scenario: Existing knowledge workflows
- **WHEN** the new project-document operations are installed or rendered
- **THEN** existing private-note search/write behavior, portal defaults and catalog-review defaults remain unchanged, and generated guidance does not imply synchronization, publication or general vault traversal authority
