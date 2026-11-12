---
id: decision/0004-knowledge-system-scope
kind: decision
scope: team
label: internal
status: accepted
sources:
  - uri: https://seanmkoval.atlassian.net/browse/KAN-454
    hash: jira-issue:KAN-454
author: human:Sean-Koval
confidence: high
valid_from: 2026-11-12
valid_to: null
review_by: 2027-05-12
supersedes: []
---
# 0004 The knowledge system is in scope

## Context

[ADR 0001](0001-refocus-ai-dlc.md) froze ai-dlc to three jobs. It kept the local
knowledge provider active and cut Confluence publication.

The knowledge system needs one record format shared by several knowledge
repositories: personal, team and one per customer. A copy of the schema in each
repository would drift. ai-dlc already has a tested knowledge-note schema, a
`knowledge` role and Pydantic-generated contracts.

## Options considered

From [KAN-454](https://seanmkoval.atlassian.net/browse/KAN-454), which supersedes
KAN-443:

1. Define the record format once in ai-dlc, and make ai-dlc the integration layer.
   Accepted.
2. Keep the schema and its validator in each knowledge repository, and leave ai-dlc
   unchanged (KAN-443).

## Decision

This record amends ADR 0001's in-scope list. These areas move to *Active*:

- The knowledge-record contract: `KnowledgeRecord`, its generated
  `contracts/knowledge-record.schema.json`, the six record templates and the format
  version that each knowledge repository pins in its `knowledge.toml`.
- The `knowledge` role, including a git repository provider.
- A new `wiki` role, with a Confluence provider as the one write path to the wiki.
- A new `transcripts` role, with Zoom and Google Meet providers.

All four are exposed through `ai-dlc mcp serve`. The contract replaces the
knowledge-note format in three steps: add (KAN-421), migrate (KAN-452), then
remove (KAN-453). Everything else in ADR 0001 and ADR 0002 stands.

## Consequences

- Knowledge-system tickets are no longer closed under the freeze. Other frozen and
  cut areas stay as they were.
- ai-dlc owns the record format; data repositories pin its version, and CI checks
  the pin.
- Field names may still change once, by decision
  [KAN-471](https://seanmkoval.atlassian.net/browse/KAN-471), before the migration.

## Links

- [KAN-454](https://seanmkoval.atlassian.net/browse/KAN-454), the decision ticket
- [KAN-421](https://seanmkoval.atlassian.net/browse/KAN-421), which records it here
- [Knowledge System spec](https://seanmkoval.atlassian.net/wiki/spaces/SD/pages/7110657)
