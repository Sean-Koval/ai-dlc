---
id: decision/0006-customer-boundary-and-promotion
kind: decision
scope: team
label: internal
status: accepted
sources:
  - uri: https://seanmkoval.atlassian.net/browse/KAN-465
    hash: jira-issue:KAN-465
author: agent:claude-code
confidence: high
valid_from: 2026-11-13
valid_to: null
review_by: 2027-05-13
supersedes: []
---
# 0006 Customer records stay in their project; promotion goes through a team source

## Context

The knowledge spec says records with `boundary: customer` never leave their
project. [ADR 0004](0004-knowledge-system-scope.md) put the record format in
ai-dlc, so ai-dlc must enforce that sentence. A team record learned from customer
work still has to say where it came from. A `derived_from` link to the customer
record would point from the team tree into the project.

## Options considered

1. A team record derives from the customer record, with an exception in the
   link rule.
2. Promotion writes a new team Source that a person sanitised, and the team record
   derives from that Source. Accepted.

## Decision

A customer record sits under `projects/<name>/` in the knowledge repository.
Only customer records of the same project may link to it. No other record may
quote eight or more words in a row of its body. No other record's `sources` may
name it or a path inside its project.

Promotion is one way. A person writes a summary with no customer names, quotes or
system identifiers. It becomes a team Source whose `sources` name no customer
path. The promoted team record derives from that Source. Nothing on the team side
links back into the project.

Index, render, `get` and `search` treat a customer record as visible only to a
caller of its own project. They call `visible_in` and `team_inputs` in
`ai_dlc.documentation.knowledge_check`, so a team or root `index.md` never lists
a customer record or links into its project.

## Consequences

- `knowledge check` fails on a misplaced customer record, an inbound or
  cross-project link, a quote, and a team citation of a customer record or path.
- The git provider's `get` and `search` take a `project`; without it, customer
  records are not found.
- The check cannot prove a summary is sanitised. The person who writes the Source
  and the reviewer of its pull request are responsible for that.
- Separate repositories per customer and cross-repository promotion (KAN-475) are
  out of scope.

## Links

- [KAN-465](https://seanmkoval.atlassian.net/browse/KAN-465), the enforcement ticket
- [ADR 0004](0004-knowledge-system-scope.md), the knowledge system scope
- [Knowledge System spec](https://seanmkoval.atlassian.net/wiki/spaces/SD/pages/7110657), section 4
