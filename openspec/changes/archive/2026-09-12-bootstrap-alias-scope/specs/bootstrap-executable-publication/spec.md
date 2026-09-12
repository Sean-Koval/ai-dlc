## ADDED Requirements

### Requirement: BP-04 Explicit shared alias publication
Source-mode bootstrap SHALL prepare the checkout's own environment without replacing an existing working shared alias, and SHALL publish the shared aliases only on explicit request or when no working alias exists. Release-mode publication SHALL be unchanged. Each prepared source environment SHALL record the checkout it was synced from, and bootstrap output SHALL identify the checkout the shared alias runs and how to use this checkout's own environment. Source and scaffold scripts SHALL remain equivalent.

#### Scenario: A linked worktree or second checkout is bootstrapped
- **WHEN** source bootstrap runs in another checkout while a working shared alias exists
- **THEN** the alias keeps resolving to the same executable, the other checkout still gets its own prepared environment, and the output names the checkout the alias runs and the command for this checkout

#### Scenario: Publication is requested
- **WHEN** source bootstrap runs with the alias publication option
- **THEN** both shared aliases resolve to the requesting checkout's environment and the output names that checkout

#### Scenario: No working alias exists
- **WHEN** source bootstrap runs with no shared alias, or with one that does not resolve
- **THEN** it publishes the aliases so the machine has a usable executable
