## MODIFIED Requirements

### Requirement: WP-02 Component digests and revision

`plugin.lock.json` SHALL record `schema`, `plugin`, `revision`, a `components` map
with one `skill:<name>` digest per included skill plus `guide:ai-dlc-workflow` and
`hooks:ai-dlc`, and `content_digest`, the SHA-256 of the canonical sorted-key JSON
of `components`. It SHALL also record `files`, the digest of every file a harness
receives from the Claude plugin other than the lock itself, and `native.codex` with
the Codex form's `content_digest` and `files`. The personal `day-start` and
`day-end` skills SHALL be excluded. The revision SHALL increase exactly when either
content digest changes. `plugin.json` SHALL carry `name: ai-dlc-workflow`,
`version: <engine>-r<revision>` and `metadata.content_digest` equal to the lock's digest.

#### Scenario: Content changes
- **WHEN** a component's content changes and the plugin is rebuilt
- **THEN** the revision and manifest version increase and the new digest appears in both files

#### Scenario: Only the Codex form changes
- **WHEN** only a Codex file changes and the plugin is rebuilt
- **THEN** the Claude content digest is unchanged and the revision increases

## ADDED Requirements

### Requirement: WP-06 Codex form

The builder SHALL write `plugins/ai-dlc-workflow/native/codex/` with every plugin skill at `skills/<name>/SKILL.md` byte-identical to the Claude plugin's, a `hooks.json` in the `.codex/hooks.json` shape whose SessionStart, PreToolUse and Stop commands run the shim, the shim itself, an `AGENTS.fragment.md` holding the guide skill's body, and a `.codex-plugin/plugin.json` manifest naming the skills and hooks.

#### Scenario: Skills match
- **WHEN** the plugin is built
- **THEN** each Codex skill's digest equals the Claude plugin skill's digest

#### Scenario: Codex loads the form
- **WHEN** the Codex form is installed as a local plugin in Codex 0.162.1 and its hooks are trusted
- **THEN** the eleven skills are listed and the PreToolUse hook blocks a destructive command

### Requirement: WP-07 Publication into a harness directory

`scripts/publish_workflow_plugin.py --harness-repo PATH` SHALL copy the Claude plugin without `native/` to `PATH/plugins/ai-dlc-workflow/` and the Codex form to `PATH/native/codex/ai-dlc-workflow/`, and print the component ids and digests to pin. `--dry-run` SHALL write nothing. It SHALL refuse when a target holds files that the previous publication's lock does not record or whose digests differ, and SHALL never write outside the two targets.

#### Scenario: An empty harness
- **WHEN** `--dry-run` runs against an empty directory
- **THEN** it lists the files and component ids and writes nothing

#### Scenario: Apply twice
- **WHEN** `--apply` runs and then runs again
- **THEN** the first writes the files and the second reports no change

#### Scenario: A hand-edited target
- **WHEN** a published file was edited in the harness
- **THEN** `--apply` refuses and leaves the file as it is
