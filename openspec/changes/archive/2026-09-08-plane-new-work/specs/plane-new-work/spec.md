## ADDED Requirements

### Requirement: PN-01 Explicit deployment and account identity
Plane SHALL support explicit Cloud HTTPS and self_hosted HTTPS or HTTP loopback origins with strict host/port parsing, no redirects, and named API-key or externally managed OAuth environment credentials. Account/workspace/project identity SHALL be revalidated without leaking credentials.

#### Scenario: A local self-hosted instance uses HTTP
- **WHEN** a reviewed origin uses localhost or literal loopback IPv4/IPv6 and an explicit valid port
- **THEN** requests may use HTTP without requiring certificate setup

#### Scenario: A reference or token changes tenant
- **WHEN** a reference crosses the configured origin/project or the authenticated user differs
- **THEN** the operation refuses before mutation

### Requirement: PN-02 Correlated bounded discovery
Create SHALL include the exact correlation as visible escaped HTML text and a scoped external pair in the same request. Find SHALL fully traverse bounded cursor pages, refusing incomplete or duplicate results. Read SHALL verify identity and correlation integrity.

#### Scenario: The correlation appears after page one
- **WHEN** complete discovery traverses multiple pages
- **THEN** it binds only the single exact scoped marker/external match

### Requirement: PN-03 Durable single-attempt mutation
Every mutation SHALL require trusted local root/state context and a durable adapter-owned intent keyed by stable operation ID and scoped payload fingerprint. Only the atomic intent insertion winner may send. Existing intent SHALL permit read reconciliation only; absent or conflicting evidence SHALL remain unresolved with actionable inspection guidance.

#### Scenario: A link response is lost and a replica is stale
- **WHEN** WorkService invokes the operation again
- **THEN** the adapter refuses a second write until an exact result can be reconciled

#### Scenario: Concurrent callers use the same operation ID
- **WHEN** both attempt to mutate
- **THEN** at most one sends and the other only reconciles

#### Scenario: Local state is unsafe or omitted
- **WHEN** ledger storage is corrupt, inaccessible, symlinked, or mutation context is absent
- **THEN** mutation refuses without fallback or a remote write

### Requirement: PN-04 Faithful lifecycle and authored links
Transitions SHALL validate current project states and distinct open/started/completed/cancelled mappings, patch only state, and refuse stale terminal reversal. Link SHALL reconcile exact scoped URLs without editing authored descriptions or titles. Shared finish gates SHALL remain unchanged.

#### Scenario: A cancelled item is presented for completion
- **WHEN** the current native state belongs to cancellation
- **THEN** it does not satisfy successful closure and is not overwritten

### Requirement: PN-05 Common optional onboarding and honest qualification
Plane SHALL use the common declarative discovery/selection/save/apply boundary and remain unnecessary for GitHub/Jira use. Verification SHALL identify fixtures, source contract revision and unverified deployment/version/live-swap evidence separately.

#### Scenario: Plane is not installed or configured
- **WHEN** a project selects GitHub or Jira
- **THEN** Plane absence does not prevent selected-provider operation
