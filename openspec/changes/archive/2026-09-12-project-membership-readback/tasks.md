# Retry Project membership readback before reporting uncertain attachment

## Implementation
- [x] 1.1 Retry the membership readback within a bound with backoff, without repeating the mutation, with regression tests.
- [x] 1.2 Keep persistent absence, conflicting item identity and ambiguous membership terminal and uncertain, with regression tests.

## Verification and delivery
- [x] 9.1 Record documentation-impact dispositions for the change.
- [x] 9.2 Validate this OpenSpec change and run required project checks.
- [x] 9.3 Update from the target branch, review the pull request, merge with fresh checks and verify merged-revision CI receipts.
