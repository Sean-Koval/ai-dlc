---
id: DEC-0007
type: decision
scope: team
status: accepted
date: 2026-11-13
owner: agent:claude-code
sources:
- resource: https://seanmkoval.atlassian.net/browse/KAN-475
  hash: jira-issue:KAN-475
links:
- type: implements
  target: DEC-0006
title: 0007 Each customer has a declared knowledge repository; promotion crosses
  repositories as a branch
label: internal
valid_from: 2026-11-13
stale_after: '2027-05-13T00:00:00Z'
confidence: high
author: agent:claude-code
aliases:
- decision/0007-customer-knowledge-repositories
---
# 0007 Each customer has a declared knowledge repository; promotion crosses repositories as a branch

## Context

[ADR 0006](0006-customer-boundary-and-promotion.md) kept customer records under
`projects/<name>/` of one repository. Client data needs a stronger line: its own
repository, access list and hosting. Transcripts already route to a customer
repository by an environment variable (KAN-457). Nothing stopped that variable from
naming the team repository or another customer's.

## Options considered

1. Records sit at the customer repository's top level, with a second placement rule.
2. The customer repository keeps `projects/<name>/` and declares itself. Accepted.

## Decision

A customer repository's `knowledge.toml` carries `[repo] boundary = "customer"`
and `project = "<name>"`. `knowledge init --customer <name>` writes it, with a
deny list, CODEOWNERS, the check workflow and no `[wiki]`.

Records keep the `projects/<name>/` placement of ADR 0006. Index, render, `get`
and `search` then need no second code path. In such a repository, `knowledge
check` also fails a record of another boundary or project. It fails a typed link
to anything outside the repository, and a source or body link that leaves it.

Render refuses a declared repository unless its `[wiki]` names the same project.
Transcript routing refuses a repository that does not declare the route's project.

`knowledge promote` writes the team Source and the derived team record on a new
branch of the team repository, through a temporary worktree. Nothing is pushed.
It refuses text with a deny-list term, a web address or a customer path. It also
refuses eight words in a row of the customer record, its Sources or their payloads.

## Consequences

- A wrong variable or a stray `[wiki]` fails closed instead of leaking.
- The deny list catches names a person listed; it cannot prove a summary is clean.
  The reviewer of the promotion pull request still owns that.
- Hosting is the company's private GitHub or the customer's own systems, as the
  contract says; ai-dlc does not choose.

## Links

- [KAN-475](https://seanmkoval.atlassian.net/browse/KAN-475), customer repositories
  and cross-repository promotion
- [ADR 0006](0006-customer-boundary-and-promotion.md), the customer boundary
