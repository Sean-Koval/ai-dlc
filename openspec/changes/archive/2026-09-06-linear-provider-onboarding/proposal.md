## Why

Replace manual team/status UUID hunting with explicit, read-only discovery and a reviewed local configuration update.
This implements the approved framework direction in [product direction](../../../../docs/product-direction.md), milestone M1.

## What Changes

- Cover multiple teams, duplicate names, two started states, pagination, authorization failure, and incomplete result handling with injected httpx responses.
- Validate UUID membership/types and config digest; preserve comments and unrelated sections; prove an invalid selection writes nothing.
- Implement provider connect preview/apply, credential-redacted errors, and binding-drift refusal. Add a sandbox read-only walkthrough procedure.

## Capabilities

### New Capabilities

- `linear-provider-onboarding`: Replace manual team/status UUID hunting with explicit, read-only discovery and a reviewed local configuration update.

### Modified Capabilities

None. Existing schema-4, content ownership, enrollment, and finish contracts remain unless an additive behavior is explicitly defined in this change.

## Impact

- Create src/ai_dlc/provider_onboarding.py
- Modify src/ai_dlc/providers/linear.py
- Modify src/ai_dlc/cli.py
- Test tests/test_provider_onboarding.py
- Modify tests/test_cli.py, tests/test_rebind.py

Dependencies: component-capability-contract.
Implementation and review evidence are recorded in the archived tasks and [execution plan](../../../../docs/superpowers/plans/2026-09-05-linear-provider-onboarding.md); merged-revision completion remains governed by the work record.
