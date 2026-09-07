## Why

Plane and Jira need the small AI-DLC tracker contract, not duplicate implementations
of their general native tools. Existing workflow code contains a GitHub-specific
capability branch. Status: proposed, pending target deployment and design review.

## What Changes

- Implement Plane and Jira Cloud tracker adapters with normalized state and reconciliation.
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
