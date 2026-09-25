## ADDED Requirements

### Requirement: EE-08 Real client driver
The runner SHALL support a driver that runs a real coding client headless with
the same client version, model and goal prompt in both arms, retains the
client's structured event stream verbatim, and reads turns, tokens and cost from
it. The goal prompt SHALL NOT contain commands, skill text or hints. A malformed
or truncated stream, or one without a final result event, SHALL make the attempt
`incomplete`.

#### Scenario: Same client in both arms
- **WHEN** a suite is planned with a real client driver
- **THEN** both arms record the same client version, model and goal prompt digest

#### Scenario: Truncated stream
- **WHEN** the client's stream ends without a final result event
- **THEN** the attempt is `incomplete` and no assertion passes

### Requirement: EE-09 Restricted egress
An attempt using a real client SHALL reach only the destinations named in the
profile, through a digest-pinned proxy on a per-attempt internal network. Refused
destinations SHALL be recorded and reported. Attempts using the deterministic
driver SHALL keep no network at all.

#### Scenario: Unlisted destination
- **WHEN** the agent connects to a host that the profile does not name
- **THEN** the connection is refused and the report names the host

### Requirement: EE-10 Credential handling and enforced budgets
The profile SHALL name a credential by environment variable only. The value
SHALL reach only the agent container and SHALL NOT appear in the plan, inputs or
evidence. A run SHALL stop before an attempt that its remaining token or spend
budget cannot cover, and SHALL report the attempts it did not start.

#### Scenario: Budget exhausted
- **WHEN** recorded spend reaches the run's limit
- **THEN** no further attempt starts and the report lists the attempts not run

### Requirement: EE-11 Git observation
Workflow assertions about commits SHALL be decided from the collected
repository by the controller, never from client output.

#### Scenario: Implementation before the work record
- **WHEN** the collected history commits implementation before any work record
- **THEN** the `ordering` assertion fails even if the client reported success
