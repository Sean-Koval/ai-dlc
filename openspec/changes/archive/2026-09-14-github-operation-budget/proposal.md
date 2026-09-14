# Bound complete GitHub Issues operations separately from requests

## Why
Finishing merged PR #116 passes specification, merge and CI gates, then twice times out during terminal Project reconciliation. The bundled provider process gets the same 30-second budget as one gh request, although reconciliation performs several independently bounded issue and Project reads. Healthy requests can exhaust the entire operation budget before final readback.

## What Changes
Give the bundled GitHub Issues provider a 120-second default process budget, leaving each gh request at 30 seconds and honoring an explicitly configured timeout. Other provider defaults, identity fingerprints, completion gates and uncertain-write recovery stay unchanged.

## Capabilities
### Added Capabilities
- github-operation-budget: Separate bounded GitHub operation and request defaults.

## Impact
Provider registry transport construction, regression tests and GitHub tracker documentation. This removes an observed completion blocker in the worktree takeover; it does not certify all live provider behavior.
