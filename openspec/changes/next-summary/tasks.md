# Replace the JSON context brief with a readable what-next summary

## Implementation
- [ ] 1.1 Derive per-record lifecycle states from local artifacts and render the fixed plain-text summary, with a fixture per state and the text asserted exactly.
- [ ] 1.2 Add `ai-dlc next [--root] [--all] [--json]`, offline, and make `context --brief` print the same text while `context` stays unchanged.
- [ ] 1.3 Include the first ten lines of the summary in the session-start hook context, with a fallback when the project cannot be read.
- [ ] 2.1 Point the tool map (repository and template) and the `day-start` skill at `ai-dlc next`.

## Verification and delivery
- [ ] 9.1 Record documentation-impact dispositions for the change.
- [ ] 9.2 Validate this OpenSpec change and run required project checks.
- [ ] 9.3 Update from the target branch, review the pull request, merge with fresh checks and verify merged-revision CI receipts.
