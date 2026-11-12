## MODIFIED Requirements

### Requirement: WP-02 Component digests and revision

`plugin.lock.json` SHALL record `schema`, `plugin`, `revision`, a `components` map
with one `skill:<name>` digest per included skill plus `guide:ai-dlc-workflow` and
`hooks:ai-dlc`, and `content_digest`, the SHA-256 of the canonical sorted-key JSON
of `components`. It SHALL also record `files`, the digest of every file a harness
receives from the Claude plugin other than the lock itself, and `native.codex` with
the Codex form's `content_digest` and `files`. The plugin SHALL include the
second-brain skills `daily-note`, `capture` and `kb-publish`. The revision SHALL increase exactly when either
content digest changes. `plugin.json` SHALL carry `name: ai-dlc-workflow`,
`version: <engine>-r<revision>` and `metadata.content_digest` equal to the lock's digest.

#### Scenario: Content changes
- **WHEN** a component's content changes and the plugin is rebuilt
- **THEN** the revision and manifest version increase and the new digest appears in both files

#### Scenario: Only the Codex form changes
- **WHEN** only a Codex file changes and the plugin is rebuilt
- **THEN** the Claude content digest is unchanged and the revision increases

#### Scenario: Second-brain skills ship
- **WHEN** the plugin is built
- **THEN** `capture`, `daily-note` and `kb-publish` have components and the removed `day-start`, `day-end`, `needs-spec` and `review-inbox` have none
