## ADDED Requirements

### Requirement: DP-01 Design intent precedes evaluation

The Design PM workflow SHALL provide a portable brief and a versioned evaluation
contract identifying audience, primary journey, constraints, criterion IDs,
evidence methods, score anchors, required checks, and run budget before generation.
It SHALL distinguish proposed defaults from human-approved task decisions.

#### Scenario: A vague design request becomes an evaluable task
- **WHEN** a user requests a good interface without criteria
- **THEN** the workflow produces a draft brief and concrete checks with explicit
  assumptions, and identifies material unresolved product decisions before implementation

#### Scenario: An established design system constrains the work
- **WHEN** the brief requires existing brand components
- **THEN** evaluation judges choices against that requirement and does not penalize
  appropriate component reuse merely for lacking novelty

### Requirement: DP-02 Evaluation preserves evidence and uncertainty

Evaluation reports SHALL identify the candidate revision, rubric version,
reviewer/session, tools used, tested states and viewports, criterion-level evidence,
findings, and verdict. Behavioral checks SHALL use pass, fail, or unverified;
subjective criteria SHALL use declared score anchors or unverified. Missing tool
access or evidence SHALL NOT count as passing behavior.

#### Scenario: A polished candidate has a broken journey
- **WHEN** a required interaction fails while visual criteria score highly
- **THEN** the report records the failed check and blocks contract acceptance

#### Scenario: Only a static mockup is available
- **WHEN** interaction verification requires a running application
- **THEN** the report can evaluate observed visual criteria but records the
  interaction checks as unverified

### Requirement: DP-03 Independent review is explicit

The workflow SHALL define generator and evaluator responsibilities independently.
An independent evaluator SHALL receive the brief, contract, candidate, and access
instructions and SHALL form findings through observation. The generator's claims
SHALL NOT substitute for evidence. Self-review SHALL be labeled as self-review.

#### Scenario: A harness lacks agent delegation
- **WHEN** parallel or delegated agents are unavailable
- **THEN** the workflow provides a separate-session or human-review handoff and
  does not report self-review as independent evaluation

### Requirement: DP-04 Iteration respects budgets and candidate identity

The workflow SHALL record iteration and time or token limits before a run, retain
candidate identities and reports, and permit selection of an earlier candidate.
It SHALL stop at contract satisfaction, budget exhaustion, a material unresolved
decision, or the declared plateau condition. Stopping SHALL NOT imply passing.
Material rubric changes SHALL create a new version and require reevaluation of
candidates compared under that version.

#### Scenario: Budget expires with a failed required check
- **WHEN** the run reaches its limit without a qualifying candidate
- **THEN** it records needs-work, unresolved findings, and the next action

#### Scenario: A later revision regresses
- **WHEN** a previous candidate meets the contract better than the latest revision
- **THEN** selection can retain the previous candidate with its matching evidence

### Requirement: DP-05 Guidance travels through existing project distribution

AI-DLC SHALL distribute Design PM instructions, templates, and examples through
its existing managed-asset and project-template mechanisms. The workflow SHALL
be usable through readable project artifacts and installed tools without a new
mandatory service. Updates SHALL preserve authored content and report conflicts.
Client-specific support SHALL be distinguished from portable instructions.

#### Scenario: A developer changes machine or harness
- **WHEN** a subsequent session opens the project
- **THEN** its saved brief, contract, candidate references, findings, and decision
  explain continuation without requiring the prior chat transcript

#### Scenario: A generated rubric has local edits
- **WHEN** asset synchronization conflicts with authored content
- **THEN** the existing ownership/conflict workflow preserves it and reports the conflict

### Requirement: DP-06 Calibration claims require measured evidence

The package SHALL include a documented calibration protocol and original sample
cases for required-defect detection and subjective rating. Results SHALL identify
the model/harness, criteria, budgets, comparisons, human ratings, and limitations.
Unrun experiments and absent human review SHALL remain explicit. Sample assets
or fixture tests SHALL NOT establish live design-quality improvement.

#### Scenario: Distribution tests pass before calibration runs
- **WHEN** generated assets and fixtures pass but no human-rated experiment exists
- **THEN** reporting states that distribution is verified and quality improvement
  remains unevaluated
