## Why

Require revision-bound documentation impact dispositions. Implements the maintainer-approved dependable documentation and knowledge plan of September 10, 2026.

## What Changes

- A shared CLI and MCP service SHALL inspect a Git comparison plus current working content, match optional catalog code, requirement and verification references, and expose changed unmapped files. Reads SHALL stay inside the repository.
- Documentation dispositions SHALL identify updated, reviewed-no-change or justified no-impact outcomes and bind inspected source and document content to evidence. Missing or changed evidence SHALL not satisfy an enabled check.
- Documentation checks SHALL be project-selectable, compare current objective findings against an explicit historical baseline, and refuse new defects without blocking solely on unchanged accepted historical findings. AI-DLC SHALL enroll after recording its baseline.

## Capabilities

### New Capabilities
- `documentation-impact-workflow`: Require revision-bound documentation impact dispositions.

### Modified Capabilities
None. Existing behavior remains compatible except the explicit opt-in extensions described here.

## Impact

Python shared services, CLI/MCP, reusable guidance, behavior tests and verification evidence. Dependencies: documentation-lifecycle-reconciliation. No publication, vault mirroring, or new model service.
