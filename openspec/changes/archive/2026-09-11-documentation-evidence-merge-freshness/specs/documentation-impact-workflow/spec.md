## MODIFIED Requirements

### Requirement: DI-02 Revision-bound dispositions
Documentation dispositions SHALL identify updated, reviewed-no-change or justified no-impact outcomes and bind inspected source and document content to evidence. Missing or changed evidence SHALL not satisfy an enabled check. Evidence recorded against a base other than the check's comparison SHALL be reported as a base mismatch naming both commits before decisions are evaluated. Recording SHALL refuse a comparison base that the checkout does not contain.

#### Scenario: Revision-bound dispositions
- **WHEN** a source changes after disposition
- **THEN** the check reports stale evidence rather than accepting the earlier review

#### Scenario: Target branch moves after disposition
- **WHEN** the branch is updated from a target branch that advanced past the recorded base and the check compares against the new target commit
- **THEN** the check fails with both commits and directs the user to record dispositions again

#### Scenario: Comparison base missing from the checkout
- **WHEN** dispositions are recorded against a target commit that the branch does not contain
- **THEN** recording refuses and directs the user to update the branch first
