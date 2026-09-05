## Why

Give agents concrete guidance and examples for choosing worthwhile product increments before writing specifications or code.
This implements the approved framework direction in [product direction](../../../docs/product-direction.md), milestone M2.

## What Changes

- Author one greenfield task and one brownfield task with evidence, options, excluded scope, RQ IDs, and a correct next action. Include a misleading feature request and contradictory requirements.
- Update the existing skills and PRD template using the examples; include exact output sections and decision rules. Follow skill-authoring guidance during implementation and retain upstream-provider routing.
- Regenerate digest locks/client copies/templates; add packaging tests for assets and behavioral scenarios measuring decisions rather than just headings.

## Capabilities

### New Capabilities

- `product-shaping-workflow`: Give agents concrete guidance and examples for choosing worthwhile product increments before writing specifications or code.

### Modified Capabilities

None. Existing schema-4, content ownership, enrollment, and finish contracts remain unless an additive behavior is explicitly defined in this change.

## Impact

- Modify agents/skills/discovery/SKILL.md
- Modify agents/skills/prd-draft/SKILL.md
- Modify agents/skills/review-inbox/SKILL.md
- Modify agents/templates/prd.md
- Create agents/templates/product-brief.md
- Create agents/examples/product-shaping/greenfield.md and brownfield.md
- Update agents/skills.lock.json and managed/generated copies
- Modify docs/workflows/greenfield.md, brownfield.md and matching project templates
- Test tests/test_templates.py and tests/test_rendering.py

Dependencies: none.
No implementation is complete. [Execution plan](../../../docs/superpowers/plans/2026-09-05-product-shaping-workflow.md).
