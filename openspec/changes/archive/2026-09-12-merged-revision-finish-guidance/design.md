# Explain and document finishing work after the target branch moves

## Context
Merged-revision evidence must come from a checkout that is exactly the merge commit, because the archive's tracked bytes and a clean `openspec/` tree are what the gate authenticates. The main checkout satisfies this only until the target branch advances. The existing reasons state the rule without the two revisions that decide it, so a correct refusal reads as a defect.

## Goals / Non-Goals
Make the refusal self-explanatory and the recovery documented. Do not relax the equality or cleanliness requirements, infer the merge commit from anything but the pull request, create or remove a worktree on the user's behalf, or change any other gate's reasons.

## Decisions
- Name both revisions and the remedy in the reason, because the blocked result is the only place a caller sees why finish refused.
- Report an unavailable HEAD separately from a mismatch: an unreadable checkout is a different failure from a moved branch.
- Keep the dirty-tree reason distinct and name the revision it inspected, so a user does not confuse dirty files with a moved branch.
- Document the temporary detached worktree procedure in the canonical workflow, and add one line to generated shared guidance so downstream projects and agent sessions see it.
- Rejected: preparing the checkout automatically, which would make a gate create working trees and hide which revision produced the evidence. Rejected: accepting a descendant of the merge commit, which would authenticate bytes the merge did not contain.

## Risks / Trade-offs
The reason grows longer. A caller that matched the old reason text verbatim must match the new text; the reasons are human-facing strings, not a stable contract.

## Migration Plan
No migration. Already finished work is unaffected; blocked work gets a more specific reason for the same refusal.
