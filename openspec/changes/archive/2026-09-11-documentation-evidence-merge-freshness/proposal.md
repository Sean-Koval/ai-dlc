# Detect documentation evidence recorded against a superseded target branch

## Why
PR #44 recorded dispositions against `2b2bd65` and passed PR CI. PR #43 then merged, and #44 merged without fresh checks. The merge-commit run compared against `059f1df` and failed with an unrelated-sounding unknown-target error, leaving `work finish` without a successful merged-revision run.

## What Changes
- The documentation gate SHALL report an evidence/comparison base mismatch, naming both commits and the update-and-re-record remedy, before validating decisions.
- Disposition recording SHALL refuse a comparison base that the checkout does not contain.
- Canonical, template and portable skill guidance SHALL require updating from the target branch and refreshing base-bound evidence and checks immediately before merge, and recommend requiring up-to-date branches.

## Capabilities
### Modified Capabilities
- documentation-impact-workflow: Revision-bound dispositions detect a moved target branch.

## Impact
Shared documentation service, its tests, development workflow, project template guidance and document skills. No CI base selection, remote repository setting, merge or evidence freshness is changed automatically.
