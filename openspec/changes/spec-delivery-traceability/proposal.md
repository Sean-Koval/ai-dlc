## Why

Give an executing agent an unambiguous connection from outcome to behavioral scenario, ticket, implementation step, and verification evidence.
This implements the approved framework direction in [product direction](../../../docs/product-direction.md), milestone M2.

## What Changes

- Add missing ID, self/cycle, absent artifact, stable order, and rich body cases; preserve old-schema defaults and correlation values.
- Validate before mutation, expose work validate, check dependency completion before branch/start effects, and render richer descriptions on first create only.
- Update skill/template examples using PS requirement IDs; show an independently finishable change and a no-spec verification item; regenerate owned copies.

## Capabilities

### New Capabilities

- `spec-delivery-traceability`: Give an executing agent an unambiguous connection from outcome to behavioral scenario, ticket, implementation step, and verification evidence.

### Modified Capabilities

None. Existing schema-4, content ownership, enrollment, and finish contracts remain unless an additive behavior is explicitly defined in this change.

## Impact

- Modify agents/skills/spec-from-prd/SKILL.md
- Create agents/templates/delivery-slice.md
- Modify src/ai_dlc/workflow.py
- Modify src/ai_dlc/cli.py
- Create src/ai_dlc/traceability.py
- Test tests/test_traceability.py
- Modify tests/test_workflow.py, tests/test_cli.py
- Update docs/workflows/design-to-implementation.md and generated templates

Dependencies: product-shaping-workflow.
No implementation is complete. [Execution plan](../../../docs/superpowers/plans/2026-09-05-spec-delivery-traceability.md).
