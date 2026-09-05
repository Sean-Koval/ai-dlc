## Why

Resolve explicitly selected provider roles into a deterministic, versioned description of required tools, guidance, configuration, and checks.
This implements the approved framework direction in [product direction](../../../docs/product-direction.md), milestone M1.

## What Changes

- Define schema-1 fixtures for openspec, linear, github-issues and two synthetic providers; add cases for missing module, unknown component, duplicate IDs, tampered digest, path escape, and no selected roles.
- Implement catalog validation and resolve_components; keep installation, network, writes, and provider operations outside the resolver. Preserve unresolved-provider diagnostics.
- Validate the three optional provider metadata fields and machine-layer refusal; document a complete third-party manifest example and verify packaged component data.

## Capabilities

### New Capabilities

- `component-capability-contract`: Resolve explicitly selected provider roles into a deterministic, versioned description of required tools, guidance, configuration, and checks.

### Modified Capabilities

None. Existing schema-4, content ownership, enrollment, and finish contracts remain unless an additive behavior is explicitly defined in this change.

## Impact

- Create src/ai_dlc/components.py
- Create modules/components.json
- Modify src/ai_dlc/config.py
- Test tests/test_components.py
- Modify tests/test_config.py

Dependencies: none.
No implementation is complete. [Execution plan](../../../docs/superpowers/plans/2026-09-05-component-capability-contract.md).
