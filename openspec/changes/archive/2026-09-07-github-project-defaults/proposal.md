## Why

The maintainer wants GitHub Projects as the default planning surface, with existing
issues organized into the repository's Project. Issue-only setup currently leaves
that essential onboarding step to the user.

## What Changes

- Default GitHub connection infers the configured repository and plans a named Project.
- Reuse an unambiguous matching Project; otherwise create and link one on saved-plan apply.
- Map verified default Status options and retain explicit custom selections and `--issues-only`.
- Preserve creation uncertainty and existing bindings; never create remote resources during preview.

## Capabilities

### New Capabilities
- `github-project-defaults`: reviewed Project creation/reuse as default GitHub onboarding.

### Modified Capabilities
None. Existing saved connection plans and lifecycle completion gates remain supported.

## Impact

GitHub onboarding, CLI option, setup documentation, tests. Applies to GitHub setup;
other providers remain behind their own capabilities. No Linear inventory required.
