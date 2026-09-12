## ADDED Requirements

### Requirement: TA-01 Stable tracker lifecycle
GitHub Issues, Plane and Jira SHALL implement the existing tracker operations and normalized states so the same WorkService lifecycle and completion policy operate through each adapter.

#### Scenario: Equivalent work uses different trackers
- **WHEN** equivalent reviewed work is published, started, read and finished through GitHub Issues, Plane and Jira
- **THEN** provider-specific requests remain inside adapters while the same local checks, spec references, and merged-revision gates apply

### Requirement: TA-02 Capability-driven behavior
Work start SHALL consume declared lifecycle capabilities without branching on tracker provider names, and legacy adapters without capability discovery SHALL retain their previous transition behavior with unverified capability reporting.

#### Scenario: A tracker lacks an in-progress state
- **WHEN** its capability result reports start-transition unsupported
- **THEN** work start reports that limitation without inventing a remote in-progress state

#### Scenario: An opted-in capability query fails
- **WHEN** a provider declares capability discovery but its response is unavailable, malformed or unsupported
- **THEN** the operation reports the failure rather than falling back to an assumed legacy capability

### Requirement: TA-03 Complete reconciliation
Tracker adapters SHALL scope correlations to the configured account and project, preserve them through remote round trips, and refuse duplicate creation when reconciliation is incomplete or uncertain.

#### Scenario: A create times out after remote acceptance
- **WHEN** its result is uncertain and the correlation is not yet visible
- **THEN** retry reports uncertainty and does not create another work item

#### Scenario: A search is truncated or ambiguous
- **WHEN** pagination is incomplete or multiple exact correlation matches exist
- **THEN** the operation fails visibly without a new create or binding change

### Requirement: TA-04 Native state fidelity
Adapters SHALL resolve valid native lifecycle transitions and verify the resulting normalized state without treating cancellation as successful completion.

#### Scenario: A Jira issue has multiple routes to the desired status
- **WHEN** the current workflow does not yield one unambiguous configured transition with satisfied required fields
- **THEN** transition refuses with actionable selection/configuration guidance rather than guessing

#### Scenario: A generic tool requests a terminal transition
- **WHEN** an invocation would bypass WorkService finish gates
- **THEN** AI-DLC's generic invocation boundary rejects it under the existing completion policy

### Requirement: TA-05 Scoped credentials and evidence
Adapters SHALL bind requests to explicit configured service identities, keep credential values outside tracked files and output, and distinguish fixture, health and live workflow evidence.

#### Scenario: The selected deployment is unsupported
- **WHEN** discovery identifies an API edition or authentication mode without an implemented adapter
- **THEN** readiness reports unsupported access instead of claiming Cloud compatibility or platform qualification

### Requirement: TA-06 GitHub Issues without board coupling
GitHub Issues SHALL be a supported tracker choice independently from GitHub Projects, and tracker selection SHALL preserve SCM configuration, PR references and existing binding identities unless an explicit reviewed change targets them.

#### Scenario: Repository issues have no configured board
- **WHEN** a user selects GitHub Issues for tracked work
- **THEN** setup requires the issue repository and authorized account but does not require a Projects board or invent an in-progress mapping

#### Scenario: A project changes its tracker
- **WHEN** tracking switches between GitHub Issues and Plane
- **THEN** its GitHub SCM, pull request and CI configuration remain unchanged and retained work is handled through explicit migration policy
