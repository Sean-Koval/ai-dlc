# Detect documentation evidence recorded against a superseded target branch

## Context
Evidence binds an exact base, the changed set and source digests. PR CI supplies the pull request base; the push run supplies the commit the merge replaced. PR checks do not rerun when the target branch moves, and re-runs reuse the original event commit and base.

## Goals / Non-Goals
Make a moved target branch obvious and actionable before merge, and keep the push-run comparison independent. Do not accept evidence for another base, rewrite evidence, change CI base selection, or change remote repository settings.

## Decisions
- Compare evidence base with the resolved comparison before decision validation, because decision targets depend on the base.
- Refuse to record dispositions for a base that is not an ancestor of HEAD; CI checkouts always contain their comparison base.
- Document the pre-merge sequence and recommend the SCM up-to-date-branch requirement as the structural control.
- Rejected: using the evidence base during push runs, which lets a stale base bypass the independent comparison. Rejected: merge-queue triggers, because exact-base evidence cannot anticipate queued predecessors.

## Risks / Trade-offs
Without the repository setting, a green PR check can still be merged after the target moves; the push run then fails visibly. Frequent target movement requires repeated re-recording.

## Migration Plan
Existing valid evidence is unaffected. Evidence already recorded against a non-contained base was never able to pass CI and must be recorded again after updating the branch.
