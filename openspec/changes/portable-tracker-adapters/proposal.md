## Why

GitHub Issues already implements the small tracker contract; extend common setup
and qualification alongside new Plane and Jira adapters, not duplicate implementations
of their general native tools. Capability-based start and GitHub setup/lifecycle are delivered by the archived
github-ticket-workflows change and PR #23. Remaining priority is Jira Cloud for
new work, with Plane optional. No Jira migration is requested. Live Jira/Plane
qualification still requires a designated environment.

## What Changes

- Integrate and qualify the existing GitHub Issues adapter; implement Plane and Jira Cloud tracker adapters with normalized state and reconciliation.
- Add optional typed capability discovery and remove provider-name branching from start.
- Supply provider-specific discovery handlers, component metadata and instructions.
- Preserve existing checks, bindings, journal behavior and terminal transition gate.

## Capabilities

### New Capabilities
- `portable-tracker-adapters`: interchangeable lifecycle operations with honest capabilities.

### Modified Capabilities
None. Existing providers keep their supported behavior and legacy contracts.

## Impact

Registry/contracts, tracker adapters, workflow start capability dispatch, provider
definitions, generated contract schemas, fixtures and live qualification evidence.
Jira Data Center is excluded until the actual work deployment is known; if required,
revise this proposed scope rather than using Cloud endpoints against it.
[Requirements](../../../docs/design/provider-toolsets-prd.md),
[plan](../../../docs/superpowers/plans/2026-09-06-portable-tracker-adapters.md).
