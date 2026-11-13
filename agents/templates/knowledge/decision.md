---
id: short-slug                # draft slug; DEC-NNNN is assigned at merge and the slug kept in aliases
type: decision
scope: team                   # personal | project | team
status: proposed              # proposed | accepted | rejected | superseded
date: YYYY-MM-DD
owner: github-login
sources:                      # what it came from (OKF sources)
  - {id: SRC-NNNN, resource: path/or/url}  # add hash: sha256:<64 hex> for a derived_from target
links: []                     # [{type: derived_from, target: SRC-NNNN}]; types: belongs_to, derived_from, supersedes, implements, codified_as, retracts
title: Short title            # shown in the OKF index
description: One line for the index
# boundary: customer          # project scope only; then phase: discovery | scoping | design | build | handoff
# domain: sdlc                # team scope only: sdlc | tooling | integration | harness
# label: internal             # internal | confidential
# tags: [topic]
# verified: {by: "human:github-login", at: YYYY-MM-DDTHH:MM:SSZ}
# valid_from: YYYY-MM-DD
# valid_to: YYYY-MM-DD        # set when superseded
# stale_after: YYYY-MM-DDT00:00:00Z
# confidence: medium          # low | medium | high
# author: human:github-login  # or agent:<model>@<digest>
# checks:                     # flightdeck.spec/v1 grammar, evaluated by flightdeck
#   - id: check-slug
#     assert: {never: {event: pr.merge}}
---
# Title

## Context

## Options considered

## Decision

## Consequences
