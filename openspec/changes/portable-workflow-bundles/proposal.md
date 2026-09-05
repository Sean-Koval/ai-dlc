## Why

Make a replaceable workflow bundle reproducible in the project repository and discoverable to the harness using existing managed rendering.
This implements the approved framework direction in [product direction](../../../docs/product-direction.md), milestone M1.

## What Changes

- Add malformed, oversized, traversal, symlink, extra-file, digest mismatch, and duplicate-name cases. Validate all assets before planning a write.
- Implement temporary source resolution, reviewed revision matching, vendored lock, and rollback on partial file errors. Preserve the existing profile-source security contract when sharing helpers.
- Extend owned skill/template rendering and project-only config validation; demonstrate one external Markdown bundle in a fresh checkout, offline.

## Capabilities

### New Capabilities

- `portable-workflow-bundles`: Make a replaceable workflow bundle reproducible in the project repository and discoverable to the harness using existing managed rendering.

### Modified Capabilities

None. Existing schema-4, content ownership, enrollment, and finish contracts remain unless an additive behavior is explicitly defined in this change.

## Impact

- Create src/ai_dlc/workflow_bundles.py
- Modify src/ai_dlc/agents.py
- Modify src/ai_dlc/cli.py
- Modify src/ai_dlc/config.py
- Test tests/test_workflow_bundles.py
- Modify tests/test_rendering.py, tests/test_templates.py

Dependencies: component-capability-contract, connected-project-readiness.
No implementation is complete. [Execution plan](../../../docs/superpowers/plans/2026-09-05-portable-workflow-bundles.md).
