# Archive delivery specifications before merge

## Why
Issue #74 makes the required archive step visible and executable before merge so the existing finish gate can succeed.

## What Changes
Add work archive, local specification status and PR warnings, and an actionable finish-gate remedy. Archive and promote through the selected OpenSpec adapter, update work references and commit only affected paths.

## Impact
Work service/CLI, OpenSpec adapter, generated shared guidance and delivery guide. Finish gate requirements stay unchanged.
