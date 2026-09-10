## ADDED Requirements

### Requirement: DI-01 Scoped impact inspection
A shared CLI and MCP service SHALL inspect a Git comparison plus current working content, match optional catalog code, requirement and verification references, and expose changed unmapped files. Reads SHALL stay inside the repository.

#### Scenario: Scoped impact inspection
- **WHEN** a mapped public interface changes
- **THEN** the matching document requires review and unmapped changes remain visible

### Requirement: DI-02 Revision-bound dispositions
Documentation dispositions SHALL identify updated, reviewed-no-change or justified no-impact outcomes and bind inspected source and document content to evidence. Missing or changed evidence SHALL not satisfy an enabled check.

#### Scenario: Revision-bound dispositions
- **WHEN** a source changes after disposition
- **THEN** the check reports stale evidence rather than accepting the earlier review

### Requirement: DI-03 Prevent new objective debt
Documentation checks SHALL be project-selectable, compare current objective findings against an explicit historical baseline, and refuse new defects without blocking solely on unchanged accepted historical findings. AI-DLC SHALL enroll after recording its baseline.

#### Scenario: Prevent new objective debt
- **WHEN** an unrelated historical finding remains while a new broken link is introduced
- **THEN** the new defect blocks and historical debt remains separately visible
