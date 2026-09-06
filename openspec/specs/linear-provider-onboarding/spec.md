# linear-provider-onboarding Specification

## Purpose
Provide complete read-only Linear discovery and an explicit, reviewed, non-secret path for configuring project team and workflow mappings without silently changing credentials, remote resources, or existing work bindings.
## Requirements
### Requirement: LN-01 Complete scoped discovery

Onboarding SHALL query only the configured credential's organization, teams, and workflow states, consume pagination, and report incomplete or failed discovery without mutations.

#### Scenario: Two started states exist
- **WHEN** a team exposes In Progress and In Review as started states
- **THEN** both are presented and explicit state selection is required

### Requirement: LN-02 Validated local preview and apply

Onboarding SHALL validate organization, team, and state membership and types before showing a non-secret patch; apply SHALL require unchanged source configuration and preserve unrelated content.

#### Scenario: Configuration changes after preview
- **WHEN** the configuration digest differs from the reviewed plan
- **THEN** apply refuses the stale patch without modifying the file

### Requirement: LN-03 Existing work and credentials stay stable

Onboarding SHALL retain the project's credential variable and refuse silent mapping changes for already bound work; it SHALL NOT create or modify remote issues or accounts.

#### Scenario: An existing binding would change
- **WHEN** apply proposes a new team for locally bound work
- **THEN** the operation refuses and names the explicit rebind workflow
