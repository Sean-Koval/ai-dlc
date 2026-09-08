# provider-toolset-onboarding Specification

## Purpose
TBD - created by archiving change provider-toolset-onboarding. Update Purpose after archive.
## Requirements
### Requirement: PT-01 Explicit provider selection
Scaffolding and adoption SHALL accept supported provider selections independently of language preset and SHALL preserve legacy defaults when those selections are omitted.

#### Scenario: A personal project chooses Plane
- **WHEN** a user selects Plane tracking and Obsidian knowledge
- **THEN** the preview selects those providers and their applicable setup/guidance without selecting Linear

#### Scenario: An existing caller omits provider options
- **WHEN** the legacy scaffold input is used
- **THEN** its prior provider defaults and applicable completion gates remain unchanged

### Requirement: PT-02 Reusable connection workflow
Connection discovery SHALL offer named authorized resources, and apply SHALL consume a reviewed non-secret plan after source, account, membership, and resource revalidation.

#### Scenario: The selected resource changes before apply
- **WHEN** configuration, account identity, membership, or a selected project/state no longer matches the saved plan
- **THEN** apply refuses without writes and requests a fresh preview

#### Scenario: A custom provider has no discovery handler
- **WHEN** guided connection is requested for that configured provider
- **THEN** the result reports unsupported guided setup without invalidating otherwise supported provider operations or inventing IDs

### Requirement: PT-03 Native harness connections
AI-DLC SHALL reuse upstream native connections and existing owned rendering to expose selected tools, preserving authored configuration and keeping credentials local.

#### Scenario: Two selected roles share a native connection
- **WHEN** two configured tool roles use identical server alias, account and endpoint bindings
- **THEN** the planned native server is deduplicated and both role instructions remain discoverable

#### Scenario: Personal and work accounts differ
- **WHEN** projects select different account aliases or endpoints
- **THEN** each project retains its own connection identity and no credentials or tickets are redirected across projects

### Requirement: PT-04 Honest capability readiness
Readiness SHALL distinguish native harness availability, AI-DLC lifecycle adapter availability, required configuration, local credential presence, and separately observed live qualification.

#### Scenario: A connector works but a lifecycle adapter is absent
- **WHEN** native tracker tools are available but the selected trusted lifecycle definition explicitly reports unavailable
- **THEN** harness support is reported separately and tracked-work operations remain unsupported

#### Scenario: Obsidian GUI is unavailable in a container
- **WHEN** note storage is configured but the optional desktop viewer is unavailable
- **THEN** readiness describes the viewing limitation without making that GUI a prerequisite for tracker operations

