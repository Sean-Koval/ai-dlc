## Why

Reconcile canonical documentation and OpenSpec lifecycle. Implements the maintainer-approved dependable documentation and knowledge plan of September 10, 2026.

## What Changes

- Roadmap and handoffs SHALL distinguish implemented, proposed, historical, cancelled and unverified scope using GitHub closure reasons and revision evidence.
- Delivered PR28 requirements SHALL be reconciled and archived using OpenSpec; canonical spec purposes SHALL describe their actual requirements. Historical Rust and decision rationale SHALL be retained.
- Every existing docs-check diagnostic SHALL be repaired or explicitly dispositioned with its path, reason and responsible role. No review date SHALL be inferred from file timestamps or test success.

## Capabilities

### New Capabilities
- `documentation-lifecycle-reconciliation`: Reconcile canonical documentation and OpenSpec lifecycle.

### Modified Capabilities
None. Existing behavior remains compatible except the explicit opt-in extensions described here.

## Impact

Python shared services, CLI/MCP, reusable guidance, behavior tests and verification evidence. Dependencies: existing merged PR28 foundation. No publication, vault mirroring, or new model service.
