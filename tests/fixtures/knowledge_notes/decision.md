---
id: decision/0007-landing-stays-in-hangar
kind: decision
scope: team
label: internal
status: accepted
sources: [{uri: "https://github.com/o/r/pull/45", hash: "git:abc123"}]
author: human:octocat
confidence: high
valid_from: 2026-10-20
valid_to: null
review_by: 2027-04-20
supersedes: [decision/0006-anyone-lands]
checks:
  - id: landing-stays-in-hangar
    scope: job
    assert: {never: {event: pr.merge, where: {hangar.pr.merged_by: {not: "hangar-landing[bot]"}}}}
    severity: warn
---
# 0007 Landing stays in hangar

Hangar lands every pull request.
