## MODIFIED Requirements

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

#### Scenario: Capture evidence identifies viewports and visible states
- **WHEN** evaluation reports observed screenshots from a running app
- **THEN** it cites the design capture manifest and files; missing capture or untested interactions remain unverified
