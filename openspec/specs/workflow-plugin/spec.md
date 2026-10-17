# workflow-plugin Specification

## Purpose
Package AI-DLC's workflow guidance, team skills and CLI-optional hooks as one opt-in,
digest-locked Claude Code plugin that a team harness can pin and switch on or off.

## Requirements

### Requirement: WP-01 Deterministic plugin build

`scripts/build_workflow_plugin.py` SHALL generate `plugins/ai-dlc-workflow/` with
`.claude-plugin/plugin.json`, `skills/ai-dlc-workflow/SKILL.md`, one
`skills/<name>/SKILL.md` per included team skill, `hooks/hooks.json`,
`hooks/aidlc_hook.py` and `plugin.lock.json`. Repeated builds from the same
sources SHALL produce byte-identical files with no timestamps, absolute paths or
machine data. The builder SHALL refuse a skill whose bytes differ from
`agents/skills.lock.json`. With `--check` it SHALL write nothing and fail when any
generated file is missing, different or unexpected; the `generated` required check
SHALL run this drift check.

#### Scenario: Two builds agree
- **WHEN** the builder runs twice without source changes
- **THEN** every file is byte-identical and the content digest is unchanged

#### Scenario: A skill changes without a rebuild
- **WHEN** an included skill changes and its lock digest is updated but the plugin is not rebuilt
- **THEN** the drift check names the stale plugin files and the required check fails

#### Scenario: A skill changes without relocking
- **WHEN** an included skill's bytes differ from its recorded lock digest
- **THEN** the builder refuses with a digest mismatch naming the skill

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

### Requirement: WP-03 Provider-neutral guide

The guide skill SHALL contain only shared guidance that holds without a concrete
project: no project check commands, provider names or provider instructions.
Guidance that needs the CLI SHALL be stated conditionally on `ai-dlc.toml` at the
repository root and `ai-dlc` on PATH, and the guide SHALL tell agents to prefer
repository-rendered skills when both are present. Included team skills SHALL guard
their `ai-dlc` command instructions with the same adoption condition.

#### Scenario: Guide content is filtered
- **WHEN** the guide is generated from the shared guidance
- **THEN** it names no project check command or provider, and every `ai-dlc` command line carries the adoption condition

### Requirement: WP-04 Opt-in loading

The manifest SHALL set `defaultEnabled` to false and declare no MCP servers or
credentials. The package SHALL pass `claude plugin validate --strict`. When it is
enabled, Claude Code SHALL expose the guide and team skills namespaced as
`ai-dlc-workflow:<skill>`.

#### Scenario: Enabled from a plugin directory
- **WHEN** a session loads the directory with `--plugin-dir` and enables `ai-dlc-workflow@inline`
- **THEN** 11 namespaced skills load and the session-start hook reports no error in a repository without `ai-dlc.toml`

### Requirement: WP-05 CLI-optional hooks

The plugin hooks SHALL run `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/aidlc_hook.py
<event>` in exec form with a 10 second timeout, PreToolUse matching
`Bash|exec_command`. The shim SHALL use only the standard library. It SHALL
delegate to `ai-dlc hook <event>` only when `ai-dlc` is on PATH, `ai-dlc.toml`
exists at the repository root and neither `HANGAR_WORKSPACE` nor `HANGAR_JOB_ID`
is set. Otherwise SessionStart SHALL print one static line (none when
`AI_DLC_HOOKS=quiet`), PreToolUse SHALL deny destructive commands with exit 2 using
the same classifier as `ai_dlc.harness.hooks` and allow everything else without
applying the bound-push policy, and Stop SHALL do nothing. `AI_DLC_HOOKS=off`
SHALL exit 0 for every event. A malformed payload, a delegate exit other than 2 or
a delegate timeout SHALL allow with exit 0. The shim SHALL NOT execute or persist
the command and SHALL NOT create `.ai-dlc/` in a repository.

#### Scenario: Hangar job in an adopted repository
- **WHEN** `HANGAR_WORKSPACE` or `HANGAR_JOB_ID` is set in an adopted repository with `ai-dlc` installed and no work record, and the payload is `git push origin feature/x`
- **THEN** the hook allows it without delegating

#### Scenario: Destructive command without the CLI
- **WHEN** `rm -rf build` arrives in any mode except `AI_DLC_HOOKS=off`
- **THEN** the hook exits 2 with a reason

#### Scenario: Adopted local repository
- **WHEN** the repository is adopted, `ai-dlc` is on PATH and no hangar variable is set
- **THEN** the hook delegates and passes through the CLI's exit 2 denial, and maps any other failure to allow

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
