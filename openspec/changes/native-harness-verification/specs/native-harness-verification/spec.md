## ADDED Requirements

### Requirement: NHV-01 Independent native readiness dimensions
Native verification SHALL report configured, rendered, recognized and authenticated separately for an explicitly selected client/root. `agents verify` SHALL generate a bounded manual procedure and validate supplied evidence without launching clients, executing model/provider calls, changing configuration or logging in. Files on disk SHALL establish only configuration/render state.

#### Scenario: Rendering succeeds without a native observation
- **WHEN** project guidance and selected client files match managed expectations but no installed-client evidence exists
- **THEN** configured/rendered may pass while recognition and authentication remain pending or not-assessed, with exit 1

#### Scenario: Local unauthenticated MCP is observed
- **WHEN** the selected local server's harmless tool works and requires no account
- **THEN** MCP functionality may pass but authentication is not-applicable rather than authenticated

### Requirement: NHV-02 Version-bound three-step evidence
Native smoke evidence SHALL bind to the complete effective-environment schema-1 configuration/observation identities, engine provenance, installed client edition/version, OS/architecture, fixture and adapter contract digests, observer role and timestamp. It SHALL independently record one benign project instruction response, one selected skill invocation and one selected harmless MCP tool outcome; discovery or self-reported recognition alone SHALL NOT satisfy invocation.

#### Scenario: Three distinct outcomes are observed
- **WHEN** an operator confirms the installed context and records matching deterministic instruction/skill markers and the harmless selected MCP result
- **THEN** validation accepts the evidence only for that context and explicitly labels its operator-attested provenance

#### Scenario: No selected skill or safe MCP tool exists
- **WHEN** the selected configuration lacks a usable reviewed skill or read-only non-billable MCP operation
- **THEN** the affected step is not-applicable or pending with a precise limitation and the output does not claim complete three-step qualification

#### Scenario: Selected transport has no safely exportable complete identity
- **WHEN** a selected MCP configuration includes opaque private transport details not covered by the effective-environment report
- **THEN** manual functional results retain that identity limitation and cannot establish reproducible full-context qualification

#### Scenario: Same package version lacks source provenance
- **WHEN** a report has a version label but cannot distinguish release/source identity
- **THEN** manual observations remain limited evidence and are not accepted as reproducible exact-context qualification

### Requirement: NHV-03 Version-aware native activation
Client adapters SHALL associate native instruction/skill/MCP schema expectations with explicitly tested client editions/versions and reviewed official sources. Known Antigravity modular-rule schemas requiring activation metadata SHALL produce valid metadata in version-scoped render plans. Root instruction recognition SHALL NOT substitute for observing modular-rule activation. Unknown contexts SHALL remain unverified and version-scoped writes SHALL be refused.

#### Scenario: Known Antigravity edition requires modular trigger metadata
- **WHEN** a version-scoped render is requested for a matching reviewed adapter entry
- **THEN** the plan includes that schema's required metadata, keeps root instruction files in their proper format and still requires separate native observation

#### Scenario: Historical UI activation instructions do not match current schema
- **WHEN** current official rules guidance and the installed edition's known schema differ from older repository instructions
- **THEN** verification names the mismatch and version-specific action without claiming the original teammate failure was caused by that mismatch

#### Scenario: Existing managed rule is edited
- **WHEN** adding activation metadata would overwrite authored edits or conflicting metadata
- **THEN** the normal ownership conflict blocks writes and preserves original bytes

### Requirement: NHV-04 Exact-context invalidation and scoped failure
Verification SHALL recompute and validate EER identities, compare current local managed state, and mark evidence stale on changed environment, client, fixture or adapter contract context. Missing, failed and stale steps SHALL retain their distinct reasons. Historical authentication SHALL remain a timestamped observation, not proof of current login.

#### Scenario: Client or managed guidance changes
- **WHEN** a client upgrades or a rendered instruction, skill or MCP configuration differs from the recorded context
- **THEN** prior evidence becomes stale and the specific affected context must be observed again

#### Scenario: New session has no fresh authentication observation
- **WHEN** earlier evidence showed authentication but current verification performs no authenticated call
- **THEN** historical authentication remains visible with its time while present-session authentication is not-assessed

#### Scenario: Evidence contains a wrong marker or malformed payload
- **WHEN** an otherwise matching step has the wrong expected result or input violates the bounded schema
- **THEN** the step fails or the input is refused respectively, independent valid results remain visible where safe and no automatic native retry occurs

### Requirement: NHV-05 Privacy cost and qualification boundaries
Shareable evidence SHALL contain only bounded logical identifiers, versions, digests, enums, markers and timestamps, excluding secrets, accounts, private paths and raw native transcripts. Default verification SHALL incur no paid model/provider run and SHALL NOT automate OAuth or copy session state. Automated fixtures SHALL prove helper behavior only; issue #53 SHALL retain actual installed-client/platform qualification scope.

#### Scenario: Native observation requires billed usage
- **WHEN** the manual smoke would need a paid model or provider operation without specific cost authorization
- **THEN** the helper leaves that observation pending and does not invoke it

#### Scenario: Unit tests pass without an installed client
- **WHEN** schema, rendering and invalidation tests pass in a fixture environment
- **THEN** the report records automated evidence while live client and Windows qualification remain pending under #53
