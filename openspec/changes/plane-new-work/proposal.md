# Optional Plane new-work lifecycle

## Why
GitHub remains the personal default and Jira Cloud the work tracker. A future local Plane deployment should support the same new-work lifecycle through configuration, without requiring Plane for other projects.

## What Changes
Add a bounded current REST work-items adapter and common declarative onboarding. Bind explicit origins/account/workspace/project and named environment credentials, retain cancellation semantics, preserve authored content, and journal adapter mutation intent before sending to prevent uncertain retries against replica-backed reads.

## Impact
Python provider/registry, common trusted definition, packaged metadata/guide, fixtures, and the bounded child spec. No deployment, installation, migration, WorkService vendor branches, live qualification or force-retry API. Parent #20/#21 qualification remains pending.
