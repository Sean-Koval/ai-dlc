# Knowledge-note frontmatter for learnings and decision records

## Why

Learnings carry only `work`, `repository`, `pr` and `tags`, so nobody can tell an
agent-written learning from a human one, or what evidence it rests on. Decision
records in adopted projects have a plain-text Status/Owner/Date header that no
tool can read, while flightdeck already evaluates `checks:` from ADR frontmatter
every night. [ADR 0001](../../../docs/decisions/0001-refocus-ai-dlc.md) keeps the
work lifecycle and the project template in scope; this change gives both one
frontmatter schema. Tracks
[#206](https://github.com/Sean-Koval/ai-dlc/issues/206) and
[#207](https://github.com/Sean-Koval/ai-dlc/issues/207).

## What Changes

- Add `contracts/knowledge-note.schema.json`, generated from
  `ai_dlc.documentation.knowledge_notes.KnowledgeNote`, with a drift check in the
  `generated` required check.
- `work finish --learning` (CLI and MCP) generates provenance frontmatter from the
  finish gate's merged PR, merge commit and CI run, or fills only missing fields of
  supplied frontmatter; the journal keeps the final note so retries are identical.
- Recall parses frontmatter: expired notes are skipped, stale ones flagged; the
  session hook prefixes them with `(stale)`.
- Add `ai-dlc knowledge check --vault PATH` to the existing `knowledge` group.
- `ai-dlc docs check` validates `docs/decisions/*.md` frontmatter, including the
  shape of `checks:` in flightdeck's `flightdeck.spec/v1` grammar, and fails when an
  accepted record's body is edited without moving to `superseded`.
- Rewrite the ADR template and the template's decisions README; back-fill ADR 0001.
- Update the `handoff` and `day-end` skills to the new format and relock digests.

## Capabilities

### New Capabilities

- `decision-records`: DR-01 to DR-04 cover the template, frontmatter validation,
  the supersede-not-edit rule and the shape of `checks:`.

### Modified Capabilities

- `session-learnings`: SL-01 and SL-02 gain provenance and frontmatter-aware
  recall; SL-04 adds `knowledge check`.

## Impact

Audience: developers recording learnings, teams adopting the decision convention,
and flightdeck's nightly ADR runner. Affected documents:
`docs/design/local-and-shared-knowledge.md`, `docs/design/project-documentation.md`,
`docs/workflows/tool-map.md`, `docs/index.md`, `contracts/README.md`,
`project-templates/project/docs/decisions/README.md`,
`project-templates/project/docs/documentation-guide.md`, the ADR template and
`docs/catalog.toml`. Evaluating checks (flightdeck), `@hangar adr`, retrieval
services and enforcing the two-person rule in code are out of scope.
