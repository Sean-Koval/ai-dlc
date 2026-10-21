---
id: decision/NNNN-short-slug
kind: decision
scope: team                  # personal | project | team
label: internal              # internal | confidential
status: proposed             # proposed | accepted | superseded | rejected
sources: []                  # [{uri: "https://github.com/o/r/pull/45", hash: "git:<merge sha>"}]
author: human:github-login   # agent-drafted: agent:<model>@<digest>, plus the PR label agent-drafted
confidence: medium           # low | medium | high
valid_from: YYYY-MM-DD
valid_to: null
review_by: YYYY-MM-DD
supersedes: []               # [decision/NNNN-older-slug]
# checks:                    # optional; flightdeck.spec/v1 grammar, evaluated by flightdeck, not ai-dlc
#   - id: landing-stays-in-hangar
#     scope: job             # turn | job | session
#     assert: {never: {event: pr.merge, where: {hangar.pr.merged_by: {not: "hangar-landing[bot]"}}}}
---
# NNNN Title

## Context

## Options considered

## Decision

## Consequences

## Links
