## MODIFIED Requirements

### Requirement: GT-02 Optional project planning states
GitHub Issues SHALL work without Projects. A configured Project SHALL use explicitly mapped single-select status options, preserving issue identity and distinguishing native issue state from planning state. Start SHALL not reopen or overwrite a terminal issue as a side effect. When the GitHub GraphQL endpoint itself refuses the request, native issue reads, closes, reopens, links and viewer checks SHALL use REST; completion SHALL then close the native issue only, report the Project as unreconciled with the reason and withhold reconciliation, while planning operations SHALL fail. Scope, rate-limit and other GraphQL failures SHALL NOT fall back.

#### Scenario: Work uses a configured Project
- **WHEN** an open issue starts with a valid in-progress mapping
- **THEN** the selected project item moves to that option while the issue remains open and both states are observable

#### Scenario: Configuration is incomplete or stale
- **WHEN** a selected project, field or mapped option cannot be verified
- **THEN** the operation fails rather than silently falling back to issue-only behavior or guessing a status by name

#### Scenario: The GraphQL endpoint is refused
- **WHEN** work finish runs where the GraphQL endpoint returns an HTTP refusal
- **THEN** the issue is read and closed through REST, the result reports the Project as unreconciled, and a start or prepare fails instead of skipping planning
