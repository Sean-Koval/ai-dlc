## Why

Issue #19 needs reusable provider onboarding for later Jira work without repeating GitHub setup or changing established saved-plan protections. Native client configuration and deferred Confluence are separate children.

## What Changes

- Trusted provider definitions describe kinds, roles and named connection selections.
- Generic CLI selections and shared discovery/plan/apply dispatch retain legacy flags.
- Common exact-plan storage, authored configuration rendering and apply safeguards serve GitHub and declarative connection handlers.
- Linear retains its canonical-digest, comment-preserving codec and gains unique named selection.

## Capabilities

### New Capabilities
- `provider-connection-service`: shared onboarding without provider-specific CLI dispatch.

### Modified Capabilities
None. Existing connection plans retain their semantics.

## Impact

Provider connection services, CLI routing and scoped tests. No remote service writes during implementation, new lifecycle adapter, client renderer, scaffold defaults, native OAuth or Confluence delivery.
