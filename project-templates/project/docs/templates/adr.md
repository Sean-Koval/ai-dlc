---
id: DEC-NNNN                  # the file's number: NNNN-short-slug.md is DEC-NNNN
type: decision
scope: team                   # personal | project | team
status: proposed              # proposed | accepted | rejected | superseded
date: YYYY-MM-DD
owner: github-login
sources:                      # evidence (OKF sources); a hash pins the version read
  - {resource: "https://github.com/o/r/pull/45", hash: "git:<merge sha>"}
links: []                     # [{type: supersedes, target: DEC-NNNN}]
label: internal               # internal | confidential
author: human:github-login    # agent-drafted: agent:<model>@<digest>, plus the PR label agent-drafted
confidence: medium            # low | medium | high
valid_from: YYYY-MM-DD
# valid_to: YYYY-MM-DD        # set when superseded
# stale_after: YYYY-MM-DDT00:00:00Z
# checks:                     # optional; flightdeck.spec/v1 grammar, evaluated by flightdeck, not ai-dlc
#   - id: landing-stays-in-hangar
#     scope: job              # turn | job | session
#     assert: {never: {event: pr.merge, where: {hangar.pr.merged_by: {not: "hangar-landing[bot]"}}}}
---
# NNNN Title

## Context

## Options considered

## Decision

## Consequences

## Links
