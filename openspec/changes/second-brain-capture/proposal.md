# Second brain phase A: capture kinds, a guarded publish op and three skills

## Why

Nothing captures daily notes, meeting transcripts or chat threads, so the
Confluence second brain has no pages. Sean decided on 2026-11-08 that the vault is
the capture surface and Confluence the durable record, published one way after
review, with work content kept behind a hard wall.
[ADR 0003](../../../docs/decisions/0003-second-brain-capture-and-publish.md)
amends the freeze for this module. Tracks
[KAN-323](https://seanmkoval.atlassian.net/browse/KAN-323).

## What Changes

- The knowledge-note schema gains kinds `daily`, `meeting` and `thread`, and the
  keys `origin`, `lane`, `source` and `publish`. Captures require `origin`;
  meetings and threads require `source`.
- `ai-dlc knowledge captured`, `publish-plan` and `publish-record` refuse a seen
  source digest, a note across the origin/site wall and a stale page version.
- The provider contract gains an optional knowledge operation, `publish`.
- New skills `daily-note`, `capture` and `kb-publish` ship in the workflow plugin.
  `day-start`, `day-end`, `review-inbox` and `needs-spec` are removed;
  `spec-from-prd` takes over the specification decision.
- **BREAKING** for anyone selecting the removed skills in `[agents] skills`.

## Capabilities

### New Capabilities

- `knowledge-capture`: KC-01 to KC-04 cover capture frontmatter, source dedupe,
  the origin/site wall and the version-guarded publish binding.

### Modified Capabilities

- `workflow-plugin`: WP-02 no longer excludes personal skills; the plugin ships
  the second-brain skills.

## Impact

Audience: the maintainer's two machines and anyone using the workflow plugin.
Affected documents: `docs/design/local-and-shared-knowledge.md`,
`docs/workflows/tool-map.md`, the project template's tool map, the plugin README,
`playbook/README.md`, `AGENTS.md`, `contracts/`. Not changed: the tracker binding
(waits for KAN-51), the `lane:*` execution labels, team-harness and cabinet. The
three Obsidian specifications stay separate: finished work records bind to them.
