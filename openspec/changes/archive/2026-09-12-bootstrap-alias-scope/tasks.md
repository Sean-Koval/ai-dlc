# Keep source bootstrap from repointing the global ai-dlc aliases

## Implementation
- [x] 1.1 Publish shared aliases in source mode only on request or when no working alias exists, with regression tests for a linked worktree, a second checkout and the opt-in path.
- [x] 1.2 Record the synced checkout in the source environment and report which checkout the shared alias runs.
- [x] 1.3 Attribute the selected shared alias to a checkout in workspace diagnostics and report another checkout as a finding, with regression tests.
- [x] 2.1 Keep the scaffold bootstrap script equivalent and update machine enrollment guidance.

## Verification and delivery
- [x] 9.1 Record documentation-impact dispositions for the change.
- [x] 9.2 Validate this OpenSpec change and run required project checks.
- [x] 9.3 Update from the target branch, review the pull request, merge with fresh checks and verify merged-revision CI receipts.
