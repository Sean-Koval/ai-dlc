---
id: DEC-0005
type: decision
scope: team
status: accepted
date: 2026-11-12
owner: Sean-Koval
sources:
- resource: https://seanmkoval.atlassian.net/browse/KAN-452
  hash: jira-comment:10482
- resource: https://seanmkoval.atlassian.net/browse/KAN-452
  hash: jira-comment:10458
links: []
title: 0005 Knowledge notes migrate to knowledge records
label: internal
valid_from: 2026-11-12
stale_after: '2027-05-12T00:00:00Z'
confidence: high
author: agent:claude-code
---
# 0005 Knowledge notes migrate to knowledge records

## Context

[ADR 0004](0004-knowledge-system-scope.md) replaces the knowledge-note format with
the knowledge-record contract in three steps: add (KAN-421), migrate (KAN-452) and
remove (KAN-453). This record is the migrate step. Decision records, learnings and
the ADR 0003 capture kinds still carry `kind:` frontmatter.

## Options considered

1. Rewrite existing files once with a reversible, idempotent command, and let
   readers accept both shapes for one release. Accepted.
2. Convert notes on read and never rewrite them. Rejected: two shapes would live on
   with no end date.
3. Switch readers to records only. Rejected: unmigrated vaults would fail at once.

## Decision

`ai-dlc knowledge migrate` rewrites frontmatter in place. It is a dry run unless
`--write` is given. It journals each original file under
`.ai-dlc/local/knowledge-migrate/`, and `--revert JOURNAL` restores them. A second
run changes nothing. Bodies are never edited.

The mappings, settled in KAN-452 and its comments 10458 and 10482:

- `kind: learning` is `type: lesson`, status `open`. `kind: decision` is
  `type: decision`, with its status kept, including `rejected`.
- The capture kinds `daily`, `meeting` and `thread` are Source records, status
  `raw`. The capture kind and `origin` become tags, and `source` becomes a
  `sources` entry with a `sha256:` hash.
- `runbook` and `note` are not record types. They stay as they are and are
  reported as legacy.
- `decision/0001-…` is `DEC-0001`. Other ids become slugs. The old id is kept in
  `aliases`, so existing links resolve.
- `review_by`, a date, is `stale_after`, midnight UTC on that date.
- `sources: [{uri, hash}]` is `sources: [{resource, hash}]`; hashes are kept.
- `supersedes`, `work` and `lane` become typed `links`. `owner` is the author's
  login. `label` and the other shared fields carry over, and `scope` is unchanged.
- A field with no mapping, such as `repository` or `publish`, is dropped and
  listed in the report.

Readers accept both shapes until ai-dlc 1.1. They are the docs gate's decision
check, recall, `knowledge check --vault` and capture dedupe. An old shape gets a
deprecation line naming that release. `work finish --learning` writes only lesson
records.

ADR 0004 partly supersedes ADR 0003, so its header carries a `supersedes` link to
`DEC-0003`. ADR 0003 stays accepted, because most of it still stands.

## Consequences

- This repository's decisions are records now, and the ADR templates emit records.
- `contracts/knowledge-note.schema.json` is still generated. KAN-453 removes it,
  with the old readers, after ai-dlc 1.0.
- A migrated capture is no longer valid input to the ADR 0003 `publish` guard.
  The `wiki` role (KAN-430) renders records instead.
- A strict bundle check would read the partial supersession as a full one.

## Links

- [KAN-452](https://seanmkoval.atlassian.net/browse/KAN-452), the migration ticket
- [ADR 0004](0004-knowledge-system-scope.md), which orders the three steps
- [KAN-453](https://seanmkoval.atlassian.net/browse/KAN-453), which removes the old format
