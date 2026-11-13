---
id: decision/0004-knowledge-system-scope
kind: decision
scope: team
label: internal
status: accepted
sources:
  - uri: https://seanmkoval.atlassian.net/browse/KAN-454
    hash: jira-issue:KAN-454
  - uri: https://seanmkoval.atlassian.net/browse/KAN-471
    hash: jira-comment:10477
author: human:Sean-Koval
confidence: high
valid_from: 2026-11-12
valid_to: null
review_by: 2027-05-12
supersedes: []
---
# 0004 The knowledge system is in scope, on Open Knowledge Format

## Context

[ADR 0001](0001-refocus-ai-dlc.md) froze ai-dlc to three jobs. It kept the local
knowledge provider active and cut Confluence publication.
[ADR 0003](0003-second-brain-capture-and-publish.md) then made Confluence canonical
for durable knowledge, with a `publish` operation on the `knowledge` role.

The knowledge system needs one record format shared by several knowledge
repositories: personal, team and one per customer. A copy of the schema in each
repository would drift. ai-dlc already has a tested knowledge-note schema, a
`knowledge` role and Pydantic-generated contracts.

Open Knowledge Format (OKF) v0.2 is a markdown container with YAML frontmatter.
Its only required key is an open `type`. No records exist yet, so field names
are cheap to align now and expensive after the migration.

## Options considered

From [KAN-454](https://seanmkoval.atlassian.net/browse/KAN-454), which supersedes
KAN-443:

1. Define the record format once in ai-dlc, and make ai-dlc the integration layer.
   Accepted.
2. Keep the schema and its validator in each knowledge repository (KAN-443).

From [KAN-471](https://seanmkoval.atlassian.net/browse/KAN-471):

1. Adopt OKF v0.2 as the container and rename three fields to OKF's names.
   Accepted.
2. Adopt OKF with no renames, and map names in an export.
3. Diverge, and borrow only `verified` and `stale_after`.

## Decision

This record amends ADR 0001's in-scope list and partly supersedes ADR 0003.
These areas move to *Active*:

- The knowledge-record contract: `KnowledgeRecord`, its generated
  `contracts/knowledge-record.schema.json`, the six record templates and the format
  version that each knowledge repository pins in its `knowledge.toml`.
- The `knowledge` role, including a git repository provider.
- A new `wiki` role, with a Confluence provider as the one write path to the wiki.
- A new `transcripts` role, with Zoom and Google Meet providers.

All four are exposed through `ai-dlc mcp serve`. The contract replaces the
knowledge-note format in three steps: add (KAN-421), migrate (KAN-452), then
remove (KAN-453).

Records are OKF v0.2 documents. `review_by` is `stale_after`, and `source` with
`source_hash` is `sources: [{id, resource, hash}]`. The classification is `label`.
Optional `title`, `description`, `tags` and `verified` are added. `status` keeps
the KAN-454 values; a fixed export maps them to OKF's draft, stable and deprecated.

Per KAN-454, the git knowledge repository is canonical, not Confluence. The wiki
is a read view: only `knowledge render` writes it, through the `wiki` role
(KAN-430). This supersedes ADR 0003's "Confluence is canonical" stance and its
`knowledge`-role `publish`. ADR 0003's capture note kinds stay until the migration
(KAN-452) and removal (KAN-453).

Everything else in ADR 0001, ADR 0002 and ADR 0003 stands.

## Consequences

- Knowledge-system tickets are no longer closed under the freeze. Other frozen and
  cut areas stay as they were.
- ai-dlc owns the record format; data repositories pin its version, and CI checks
  the pin. A repository's root `index.md` declares `okf_version: "0.2"`.
- A `derived_from` link needs a hashed `sources` entry for its target, and one
  record may cite several sources.
- ai-dlc claims OKF conformance only and takes no code dependency on it. OKF is
  young and may change.

## Links

- [KAN-454](https://seanmkoval.atlassian.net/browse/KAN-454) and
  [KAN-471](https://seanmkoval.atlassian.net/browse/KAN-471), the decision tickets
- [KAN-421](https://seanmkoval.atlassian.net/browse/KAN-421), which records them here
- [ADR 0003](0003-second-brain-capture-and-publish.md), partly superseded here
- [Knowledge System spec](https://seanmkoval.atlassian.net/wiki/spaces/SD/pages/7110657)
