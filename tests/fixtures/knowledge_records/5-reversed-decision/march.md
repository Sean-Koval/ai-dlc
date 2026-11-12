---
id: DEC-0003
type: decision
scope: team
status: superseded
date: 2026-03-04
owner: sean
sources:
  - {resource: https://example.invalid/pr/12}
links: []
valid_from: 2026-03-04
valid_to: 2026-09-15
aliases: [nightly-builds-only]
checks:
  - id: nightly-only
    assert: {never: {event: pr.merge}}
---
# Nightly builds only
