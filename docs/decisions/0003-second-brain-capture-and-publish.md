---
id: DEC-0003
type: decision
scope: team
status: accepted
date: 2026-11-08
owner: agent:claude-code
sources:
- resource: https://seanmkoval.atlassian.net/browse/KAN-323
  hash: jira-issue:10366
links: []
title: '0003 The second brain: capture note kinds and one Confluence publish op'
label: internal
valid_from: 2026-11-08
stale_after: '2027-05-08T00:00:00Z'
confidence: high
author: agent:claude-code
aliases:
- decision/0003-second-brain-capture-and-publish
---
# 0003 The second brain: capture note kinds and one Confluence publish op

## Context

[ADR 0001](0001-refocus-ai-dlc.md) keeps the local knowledge provider in scope
but cuts Confluence publication. A review of the second brain on 2026-11-08 found
that nothing captures daily notes, meeting transcripts or chat threads. Two earlier
attempts stalled before the first useful note.

Sean decided the shape the same day. Confluence is canonical for durable
knowledge. Obsidian is the capture surface for daily notes and transcript drops.
Publishing is one-way and reviewed. Work content never leaves the work machine
and the company's systems, so there are two vaults and two Atlassian sites.

## Options considered

1. Amend the freeze for a second-brain module in ai-dlc. Accepted.
2. Put capture and publish in team-harness. Rejected: that repository defines what
   hangar sandboxes run, and the second brain runs in interactive sessions on two
   machines.
3. Use a two-way Obsidian and Confluence sync tool. Rejected: every tool reviewed
   is one-way or lossless for only part of the format.

## Decision

Sean approved this amendment on 2026-11-08. The in-scope list of ADR 0001 gains a
second-brain module with exactly these parts:

- The capture note kinds `daily`, `meeting` and `thread` in the knowledge-note
  schema. Each names its `origin` vault, `work` or `home`, and may name a `lane`,
  which is a tracker epic key. Meetings and threads record a `source` digest.
- One optional knowledge operation, `publish`: one reviewed note to one page. A
  bound note records `publish.page_id` and `publish.version`.
- The `daily-note`, `capture` and `kb-publish` skills in the workflow plugin.
  They replace `day-start`, `day-end`, `review-inbox` and `needs-spec`.

Three rules bind the code. Each vault declares its origin and its one site; there
is no default. A note whose origin or site differs from the vault's is refused
before anything leaves the machine. A page that changed since its last publish is
refused, not overwritten.

ai-dlc itself never calls Confluence or files tickets. The agent publishes through
the client's approved Atlassian connection after the user confirms the exact page.

Everything else in ADR 0001 and [ADR 0002](0002-jira-work-tracker-and-trace-correlation.md)
stands, including the frozen tracker binding until KAN-51.

## Consequences

- Phase A is usable without new approvals. Sean uses it for two weeks before any
  further capture work is built.
- Filing proposed tickets from a capture, scheduled home-vault runs and any Zoom or
  Meet integration need their own decision.
- A capture never stores a raw transcript, only its path and digest.

## Links

- [KAN-323](https://seanmkoval.atlassian.net/browse/KAN-323), which implements this
- [Local and shared knowledge](../design/local-and-shared-knowledge.md)
