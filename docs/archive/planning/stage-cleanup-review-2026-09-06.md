> Historical record. Retained for provenance, not current implementation guidance.
> Consult docs/index.md, canonical OpenSpec requirements and the tracker.

# Scoped failed-stage remediation and independent review

Historical September 6 assessment. Current choices, priority and repair evidence
are in [the current roadmap](../../roadmap.md) and the September 7 verification records.
This document does not authorize a Linear call or change the current GitHub-first scope.

Baseline: `ab1f15bee6a730f4980d6f2ce096ce6dd6e51cc0`, including fix `19809bc`.
Work: SAN-12 / `portable-workflow-bundles` on `codex/portable-workflow-bundles`.
The maintainer authorized one further TDD remediation and independent review
cycle on September 6, 2026. This report records that cycle only.

## Finding and design decision

Rollback verified a stage and then unlinked its pathname. A replacement inserted
between those operations was deleted. Failed stage creation had the same gap.
Real-file tests reproduced data loss in both paths before implementation.

Moving the stage to a random quarantine followed by another check/unlink would
relocate the gap under the same-user concurrent mutation model. The platform
APIs delete a pathname rather than condition deletion on an expected inode.
See the [Linux unlinkat manual](https://man7.org/linux/man-pages/man2/unlinkat.2.html)
and [Apple unlink manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/unlink.2.html).

The repair uses conservative retention, not an atomic-delete claim. Failed
stages, including partial files and files displaced during rollback, are not
deleted or rewritten. Transaction destinations are restored where safe.
The original failure receives notes identifying retained stages for inspection.
The user was offered a broader staging redesign; no broader implementation was
selected in this cycle.

## TDD and review evidence

- Two delete-boundary cases failed because the authored replacement disappeared.
- A third case failed because rollback removed all stages instead of retaining
  and reporting them. It now verifies exact destination restoration and the
  original exception object, plus reported residue.
- Independent review found that a partial stage created during a failed recovery
  attempt was retained but its diagnostic note was discarded. Two further cases
  failed for missing notes: one failed attempt followed by successful retry, and
  two failed attempts. Both recovery handlers now forward those notes to the
  original failure with destination context.
- All 46 rendering tests passed after that correction. The independent reviewer
  also ran real-file recovery-sync failures for one and two failed attempts and
  accepted the scoped remediation with no remaining findings in its diff.
- Final focused verification passed 746 tests. The final required project check
  passed generated, format, lint, types, and test outcomes, with 1,141 full tests
  passing. Strict OpenSpec validation and patch hygiene passed. These are local
  checks of the repair before commit, not merged-revision CI or live-platform
  qualification. See the [executor handoff](../../handoffs/framework-delivery.md).
  Earlier 744-focused and
  1,139-full passes preceded the note-forwarding correction and are not its final
  evidence.

## Remaining boundary and recovery procedure

Whole SAN-12 review is not accepted: successful-transaction backup deletion still
checks backup identity separately from unlink. That adjacent path was not part
of this narrowly scoped failed-stage repair. Resolving it needs an explicit
cleanup design/scope decision rather than another quarantine check/unlink.
OpenSpec archive, PR/CI/merge, and `work finish` were not attempted.

After a failed render, inspect the exception's retained filenames/paths. Stop
concurrent writers, inspect each file, and preserve any authored bytes before
deliberate manual removal. A directory moved by another writer can move the
reported file outside its original project-relative location. Never bulk-delete
`.ai-dlc-*` by naming convention. A later render must not adopt retained stages
as trusted inputs.

SAN-12's last known tracker state is In Progress. A fresh status request failed
because `LINEAR_SANDBOX_TOKEN` was absent from the selected environment; no live
tracker status is claimed. The Plane/Jira/Confluence request is recorded in the
[separate provider assessment](provider-substitution-2026-09-06.md).
