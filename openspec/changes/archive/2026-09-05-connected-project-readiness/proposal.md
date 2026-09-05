## Why

Join selected provider requirements with machine provisioning and expose actionable project readiness without confusing it with release certification.
This implements the approved framework direction in [product direction](../../../docs/product-direction.md), milestone M1.

## What Changes

- Add injected-probe tests for absent binary, absent guidance, absent env key, valid offline requirements, and headless capability; test that outputs never contain credential values.
- Forward optional root through public commands, manager, and provisioning; union modules using CC-01 and preserve explicit profile/machine precedence and no-root behavior.
- Render an owned provider/tool index into supported client guidance; implement project readiness and add diagnostics to doctor without overriding machine enrollment failures.

## Capabilities

### New Capabilities

- `connected-project-readiness`: Join selected provider requirements with machine provisioning and expose actionable project readiness without confusing it with release certification.

### Modified Capabilities

None. Existing schema-4, content ownership, enrollment, and finish contracts remain unless an additive behavior is explicitly defined in this change.

## Impact

- Create src/ai_dlc/readiness.py
- Modify src/ai_dlc/cli.py
- Modify src/ai_dlc/machine.py
- Modify src/ai_dlc/provision.py
- Modify src/ai_dlc/agents.py
- Test tests/test_readiness.py
- Modify tests/test_machine.py, tests/test_cli.py, tests/test_rendering.py

Dependencies: component-capability-contract.
No implementation is complete. [Execution plan](../../../docs/superpowers/plans/2026-09-05-connected-project-readiness.md).
