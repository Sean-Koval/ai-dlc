# Capture session learnings at finish and recall them at work start

## Implementation
- [x] 1.1 Store an optional learning note at finish through the knowledge provider's idempotent `note` operation under a journaled operation identity, with regression tests for a retried finish, a finish without a learning and a failing provider.
- [x] 1.2 Add read-only bounded recall to the knowledge module and to `work start`, with tests for a matching title word, a matching specification name, no vault and no match.
- [x] 1.3 Count friction per session in the hook and add the stop reminder at the threshold, with tests on both sides of the threshold.
- [x] 1.4 Append recalled learnings to the `session-start` hook context.
- [x] 2.1 Define the learning note format in the knowledge design document; point `day-end` and `handoff` at it and make `day-start` read recalled notes; render the skills.
- [x] 2.2 Document `--learning` and the recall in both tool maps.

## Verification and delivery
- [ ] 9.1 Record documentation-impact dispositions for the change.
- [ ] 9.2 Validate this OpenSpec change and run required project checks.
Integration follow-up: the maintainer completes fresh-base PR review, merge, merged-revision CI receipts, and `ai-dlc work finish`. These post-review actions are not implementation qualification evidence.
