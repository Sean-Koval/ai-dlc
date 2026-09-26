# Concise team skill context design

## Authority, scope and delivery

Draft work ID: `concise-team-skill-context`. Owner: repository maintainers.
The user's team-flow efficiency request authorizes specification followed by
implementation; this document proposes the bounded behavior for that delivery.
`requires_spec=true` because agents receive different generated context.
Review/publication status belongs to the parent-managed work record and tracker,
not to an implied approval in this file. There are no delivery dependencies on
other team-flow changes; this change uses the already delivered team-sources and
native-work-harnesses contracts.

This slice changes only how selected team skills appear in generated guidance.
It does not alter packaged or bundled skills, roles/tags, source subscriptions,
sync activation, MCP/hook configuration, model routing, token estimation or native
client capabilities. No new framework, configuration flag or external call is
needed.

## Observed implementation and contract clarification

`merge_source_items` inserts complete skill and rule bodies into its returned
team section. `_render_agents` appends that section to `AGENTS.md`; Claude's
`CLAUDE.md` references AGENTS, and Antigravity's managed rule repeats the guidance.
The same skill bodies are written to client skill files. Source skill provenance
and hashes are tracked in `.ai-dlc/agent-ownership.json`; source locks are verified
before render and team renders already use the transactional writer.

TS-02 currently says a selected skill appears in AGENTS.md and client skill files.
That wording does not distinguish discovery from loading instructions; its delta
makes the intended indexed appearance explicit. Full rule content stays inline.
Native-layout skills currently need only nonempty UTF-8 Markdown; imposing valid
YAML frontmatter would break existing accepted sources. Teamai's existing strict
metadata checks remain authoritative and are not relaxed by this change.

## Intended representation

Keep the current selected-source traversal and collision checks. Continue adding
exactly `item.body` to the skill export map. Build a deterministic index entry
for each selected skill with its validated name, source ID, a short description,
and links to the SKILL.md destinations actually included in this render. Use the
existing client-directory mapping passed from the renderer; do not duplicate it
inside a source-format adapter. Deduplicate destinations shared by Codex and
Antigravity, while labeling the applicable clients. A Claude-only render links
`.claude/skills/<name>/SKILL.md`; Codex or Antigravity links
`.agents/skills/<name>/SKILL.md`. A combined render includes both unique paths.
An explicit client render indexes that render's destinations and preserves files
outside its scope under the existing ownership rules.

Use a safely parsed YAML frontmatter `description` when it is a nonempty string.
Collapse whitespace, remove nonprinting control characters, and limit the result
to 240 Unicode characters, including a visible ellipsis when truncated. Escape
Markdown/HTML punctuation so metadata cannot add headings, links or managed
markers to generated guidance. Missing, malformed, non-string or empty optional
description metadata uses the fixed fallback `Read the linked skill for its
instructions.` Do not derive a description from arbitrary body paragraphs, add a
new manifest field, rewrite frontmatter or reject an otherwise valid native
source. Keep safe parsing within the existing bounded input constraints; use the
existing YAML dependency, with no executable YAML constructors.

Use repository-relative, angle-bracket Markdown destinations compatible with the
existing Antigravity `_rule_links` rebasing. Since names and source IDs are
validated slugs, destination construction cannot use description text. Test
resolved link targets from both repository-root guidance and
`.agents/rules/ai-dlc.md`, rather than assuming a root-relative link works from
every file. Retain existing full rule semantics; do not rewrite their content as
a consequence of rendering a skill index.

Precede the index with concise guidance to read an applicable skill's linked file
before using it. This is also the manual fallback when native skill discovery is
unavailable or unqualified. Do not claim native recognition based on file output.
If the effective render client list is empty, there is no native destination:
keep complete selected skills inline, preserving access with no extra generated
directory or configuration. Unsupported client names continue to refuse through
the existing adapter boundary.

## Migration and recovery

There is no new persistent generated metadata: the index lives in the existing
managed guidance section. An intact old section upgrades on ordinary render;
`--check` reports the planned change without writing. Marker hashes update through
`managed_section`. Existing `files`, `source_skills` and `source_directories`
ownership retains its shape and provenance. Do not adopt an authored index or
skill file, create a second ownership system or reset hashes to suppress conflicts.

Continue refusing edited managed guidance, edited owned skill files and local
name collisions before any output changes. Authored text outside managed sections
and native activation metadata survive. Deselecting or updating a source updates
the index and active skill files together using the current transaction and
retained-backup behavior. Reselecting restores files without adopting recovery
backups. A render following successful explicit sync sees the new description
and body; a remote ref advance alone changes neither. Codex/Antigravity's shared
path remains one owned export.

## Verification and byte evidence

TS-02 maps to selection and exact-export tests in `tests/test_team_sources.py`.
TS-05 maps to description escaping/fallback, unique destinations, clientless
fallback and actual-link-resolution tests there and in
`tests/test_native_harnesses.py`. TS-06 maps to old-output migration, dry-run,
conflict, deselection/reselection, sync and transactional recovery tests.
TS-07 maps to a deterministic long-body fixture: hold metadata/rules constant,
render a short then long skill body, and assert equal generated guidance sizes
and different exact skill-file sizes. Compare the long fixture's new UTF-8
managed-guidance byte count with its explicit legacy inline representation and
record both counts in test evidence. The compact representation must be smaller
for that fixture; no guarantee applies to every tiny skill or the clientless
fallback. No network, token conversion, dollar estimate or client qualification
is involved.

## Documentation and next action

Update the enrollment runbook's duplicated-body guidance with index/discovery,
manual fallback, migration and the empty-client exception. Review architecture,
release limits and catalog mappings against the final changes; use the project's
documentation impact/review workflow for content-bound dispositions. Keep fixture
execution notes under ignored `.ai-dlc/local/`, not another durable report.
Proceed to implementation after parent review/validation and tracker preparation
under the user's existing authorization; there is no unresolved product choice.
