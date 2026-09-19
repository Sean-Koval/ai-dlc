## ADDED Requirements

### Requirement: EE-01 Offline plan
`ai-dlc eval plan <suite> --profile <profile>` SHALL validate the suite and profile
against their versioned contracts and print the full scenario, arm and attempt
matrix with installation source, required resources, assertions and budgets. It
SHALL NOT start a container, open a network connection or read a credential value.

#### Scenario: Valid suite
- **WHEN** a suite with two scenarios, both arms and one attempt is planned
- **THEN** four attempts are listed with their image digest, engine artifact hash, limits and assertion identifiers, and no Docker or network call is made

#### Scenario: Secret in a scenario or missing budget
- **WHEN** a scenario embeds a credential value, or the profile omits model, token or spend settings
- **THEN** planning refuses and names the offending field

### Requirement: EE-02 Isolated attempts
Each attempt SHALL run in a new container with a new home, project, machine
binding and vault, and SHALL NOT mount the development checkout or any host path.
The treatment arm SHALL run in a prebuilt candidate image in which the candidate
wheel was installed at image build time; the profile SHALL record the wheel's
hash and the image identity. Release mode SHALL require published, hash-verified
assets. Docker being unavailable SHALL produce an `infrastructure` outcome with no
host fallback.

#### Scenario: Two consecutive attempts
- **WHEN** an attempt writes files to its home and project and a second attempt starts
- **THEN** the second attempt observes none of them

#### Scenario: Limits
- **WHEN** an attempt exceeds its timeout, is cancelled, or exceeds a resource limit
- **THEN** it is stopped, evidence collected so far is retained, and the outcome is `incomplete` or `infrastructure` with the limit named

### Requirement: EE-03 Evidence outside the agent's reach
Expected answers, hidden tests and the evidence collector SHALL stay outside the
attempt's writable environment. Evidence SHALL be collected before cleanup, and a
cleanup failure SHALL be recorded in the run directory.

#### Scenario: Cleanup fails
- **WHEN** container removal fails after evidence collection
- **THEN** the report keeps the evidence, records the failed cleanup and the resource identifier, and does not report the attempt as clean

### Requirement: EE-04 Separate results that cannot pass on absence
Reports SHALL grade workflow, correctness and quality separately. Every assertion
SHALL record its expected condition, observation and evidence references. Quality
SHALL remain `pending` until a human records it. A missing mandatory observation
SHALL NOT produce `pass`, and assistant or driver text claiming success SHALL NOT
count as evidence.

#### Scenario: Forged completion
- **WHEN** the transcript states that all tests pass but the hidden tests fail on the collected tree
- **THEN** correctness is `fail`

#### Scenario: Missing observation
- **WHEN** a mandatory event source is absent, malformed or truncated
- **THEN** the affected dimension is `unavailable` or `incomplete`, never `pass`

#### Scenario: Secret in evidence
- **WHEN** collected evidence contains the value of a profile-named credential variable
- **THEN** the run fails with a redaction error and the value is not written to the report

### Requirement: EE-05 Baseline arm
Every scenario SHALL be runnable in a `treatment` arm and a `baseline` arm that
share fixture content, goal, bounded answers, limits and driver. The baseline
image SHALL contain no AI-DLC installation or generated guidance. The treatment
image SHALL be the baseline image with the candidate installed in added layers
only, and a run SHALL refuse a treatment image that is not derived from the
baseline image layer for layer. Hidden acceptance tests SHALL be graded on the
baseline image for both arms. Workflow assertions SHALL apply only to the
treatment arm. The report SHALL state per scenario the difference between arms in
correctness, turns, wall time and metered usage, together with the number of
attempts per arm.

#### Scenario: Arms differ in anything else
- **WHEN** a scenario tries to give an arm its own fixture, goal, answers or limits
- **THEN** planning refuses and names the field

#### Scenario: Treatment image not derived from the baseline
- **WHEN** the treatment image is identical to the baseline image or does not start with all of its layers
- **THEN** the run refuses before any attempt starts

#### Scenario: Single attempt
- **WHEN** each arm has one attempt
- **THEN** the report shows both results and the differences, and labels them as one attempt without a claim that either arm is better

### Requirement: EE-06 Reports rebuild from retained evidence
`ai-dlc eval report <run-directory>` SHALL rebuild JSON, JUnit and a readable
failure timeline from the run directory alone, and the run directory SHALL hold
enough recorded input to rerun the same scenario against another candidate.

#### Scenario: Rebuild offline
- **WHEN** report runs with no Docker and no network
- **THEN** it produces the same results as the original run and identifies the failed stage and its evidence

### Requirement: EE-07 Existing interfaces preserved
Provider conformance testing and the prompt-only skill evaluation SHALL keep
their current commands, inputs and outputs. Fixture evidence SHALL be labelled as
fixture evidence and SHALL NOT qualify live behavior.

#### Scenario: Existing suites
- **WHEN** the existing provider conformance and skill evaluation tests run
- **THEN** they pass unchanged
