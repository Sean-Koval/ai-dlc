# jira-cloud-new-work Specification

## Purpose
Provide scoped Jira Cloud onboarding and correlated issue creation, reviewed fields, faithful transitions and links while enforcing selected account identity and bounded qualification claims.
## Requirements
### Requirement: JC-01 Explicit scoped Cloud identity
Jira requests SHALL use a selected Cloud UUID/site/account/project/standard issue type and explicit oauth_bearer or personal_scoped_token_basic environment credentials. Requests SHALL refuse redirects, foreign references, mismatched Cloud/account identity and unsupported editions without credential-bearing diagnostics.

#### Scenario: A credential points to another account
- **WHEN** authenticated myself or serverInfo differs from reviewed identity
- **THEN** the operation refuses before any mutation

### Requirement: JC-02 Correlated complete publication
Create SHALL preserve the exact correlation in ADF text and a same-create scoped property, then fresh-read both. Reconciliation SHALL fully traverse bounded enhanced search, reject incomplete or duplicate matches, and preserve shared uncertain-create no-retry behavior.

#### Scenario: A create response is lost and search is delayed
- **WHEN** shared WorkService retries with an uncertain journal and no visible correlation
- **THEN** it refuses a second create until existing identity can be reconciled

#### Scenario: Correlation evidence is damaged or search truncated
- **WHEN** the expected property and marker disagree, multiple matches exist, or pagination is incomplete
- **THEN** publication refuses without creating or binding a replacement

### Requirement: JC-03 Reviewed create fields
Create SHALL revalidate selected project/type and current field metadata, preserve reserved generated fields, and require explicit supported values or usable server defaults for required fields.

#### Scenario: A new required custom field appears
- **WHEN** its reviewed supported value or usable default is absent
- **THEN** create refuses before mutation and identifies the field without guessing a value

### Requirement: JC-04 Faithful lifecycle transitions
State normalization SHALL use explicit disjoint successful/cancelled mappings and SHALL NOT infer completion from Done category. Transition SHALL use current available routes and reviewed supported field values, reject ambiguity and verify resulting state. Existing shared finish gates SHALL remain authoritative.

#### Scenario: A completion transition produces cancellation
- **WHEN** the resulting status or resolution maps to cancellation
- **THEN** completion is refused and is not reported as closed

#### Scenario: Two eligible transitions lead to a target status
- **WHEN** no reviewed transition ID uniquely selects a route
- **THEN** the provider refuses before a transition mutation

### Requirement: JC-05 Shared onboarding and links
Jira setup SHALL use the common declarative connection service with complete named resources and authored-safe saved apply. Tracker links SHALL use scoped deterministic remote-link identity and reconcile without modifying authored description.

#### Scenario: A shared work record links a pull request twice
- **WHEN** the same scoped URL is already linked
- **THEN** the existing remote link is retained without a second creation or authored-description edit

### Requirement: JC-06 Bounded evidence
Verification SHALL distinguish real local/HTTP-transport fixture execution from actual company tenant, permission, workflow and platform qualification. Plane, native login and migration SHALL NOT be implied by this child.

#### Scenario: Fixture lifecycle passes
- **WHEN** simulated HTTP responses exercise the shared WorkService
- **THEN** evidence leaves real company authentication, permissions and disposable live probe pending

