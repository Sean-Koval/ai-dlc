# Keep work state separate from documentation evidence

## Why
Tracker and PR links alter work records without changing documentation. Their independent required validation should own this state.

## What Changes
Exclude work records from documentation snapshots unless explicitly mapped by the catalog. Code, specifications and other changed files retain content-bound review.

## Capabilities
### Modified Capabilities
- documentation-impact-workflow: work-record exclusions with explicit mapping preservation.

## Impact
Documentation impact service, regression tests and project documentation ownership guide.
