---
id: DEC-0002
type: decision
scope: team
status: accepted
date: 2026-11-04
owner: Sean-Koval
sources:
- resource: https://seanmkoval.atlassian.net/browse/KAN-267
  hash: jira-comment:10241
- resource: https://seanmkoval.atlassian.net/browse/KAN-268
  hash: jira-comment:10242
links: []
title: 0002 Jira Cloud is the work tracker, and ai-dlc correlates traces
label: internal
valid_from: 2026-11-04
stale_after: '2027-05-04T00:00:00Z'
confidence: high
author: human:Sean-Koval
aliases:
- decision/0002-jira-work-tracker-and-trace-correlation
---
# 0002 Jira Cloud is the work tracker, and ai-dlc correlates traces

## Context

[ADR 0001](0001-refocus-ai-dlc.md) froze the Jira Cloud adapter to bug fixes. It
also left ai-dlc with no part in agent traces: hangar runs agents and flightdeck
judges them. ADR 0001 says a later decision may reopen a frozen area.

Two needs came up when the suite started to serve work use. Work is tracked in
Jira project KAN, including decisions only a person can make, and hangar takes
intake from Jira. Flightdeck and trace compiler need to know which ticket and
which CI receipt a trace belongs to.

## Options considered

For the work tracker ([KAN-268](https://seanmkoval.atlassian.net/browse/KAN-268)):

1. Jira Cloud is the qualified work tracker. Accepted.
2. GitHub Issues stays the default and Jira stays optional and unqualified.
3. GitHub keeps delivery, and `work finish` writes outcomes to a linked Jira ticket.

For traces ([KAN-267](https://seanmkoval.atlassian.net/browse/KAN-267)):

1. Correlate, don't emit: sessions carry a join key. Accepted.
2. Add a local trace exporter to ai-dlc.
3. No change, so only hangar-run work is measured.

## Decision

The Jira Cloud adapter moves from frozen to active. Once live qualification
passes, it is the one qualified work tracker in the README and provider guidance.
The GitHub Issues and Projects adapters stay frozen and keep working.

The workflow plugin gives each session it starts a join key: the work ID and the
tracker key of the active work record. ai-dlc still runs no agents and captures or
exports no traces. Hangar captures them, and flightdeck and trace compiler join
them on that key.

Everything else in ADR 0001 stands. Read the two records together.

## Consequences

- The README and provider guidance name Jira Cloud as qualified only after a
  dated live record against KAN
  ([KAN-51](https://seanmkoval.atlassian.net/browse/KAN-51), then
  [KAN-286](https://seanmkoval.atlassian.net/browse/KAN-286)).
- The join key's field names are agreed with trace compiler and written down in one
  place ([KAN-285](https://seanmkoval.atlassian.net/browse/KAN-285)).
- A trace exporter, a local runner or trace storage in ai-dlc remains out of scope.

## Links

- [KAN-267](https://seanmkoval.atlassian.net/browse/KAN-267) and
  [KAN-268](https://seanmkoval.atlassian.net/browse/KAN-268), the decision tickets
- [KAN-284](https://seanmkoval.atlassian.net/browse/KAN-284), which records them here
