## Why

Make a replaceable workflow bundle reproducible in the project repository and discoverable to the harness using existing managed rendering.
This implements the approved framework direction in [product direction](../../../docs/product-direction.md), milestone M1.

## What Changes

- Add duplicate-key-safe loading plus malformed, oversized, traversal, symlink,
  non-regular, extra-file, digest, duplicate name/path, exact export coverage, and
  portable skill-frontmatter cases. Validate all assets before planning a write.
- Implement portable temporary source resolution, reviewed revision matching at
  the service boundary, requested/manifest ID equality, the fully specified
  vendored lock, guarded same-owner updates, and rollback on partial file errors.
  Preserve the existing
  profile-source security contract when sharing helpers.
- Keep import separate from activation. Extend owned skill/template/index
  rendering, project-only config validation, and bundle-aware readiness;
  demonstrate one external Markdown bundle in a fresh checkout with its source
  unavailable.

## Capabilities

### New Capabilities

- `portable-workflow-bundles`: Make a replaceable workflow bundle reproducible in the project repository and discoverable to the harness using existing managed rendering.

### Modified Capabilities

None. Existing schema-4, content ownership, enrollment, and finish contracts remain unless an additive behavior is explicitly defined in this change.

## Impact

- Create src/ai_dlc/workflow_bundles.py
- Modify src/ai_dlc/profile_source.py
- Modify src/ai_dlc/agents.py
- Modify src/ai_dlc/cli.py
- Modify src/ai_dlc/config.py
- Modify src/ai_dlc/readiness.py
- Test tests/test_workflow_bundles.py
- Modify tests/test_profile_source.py, tests/test_rendering.py,
  tests/test_templates.py, tests/test_config.py, tests/test_readiness.py, and
  tests/test_cli.py

Dependencies: component-capability-contract, connected-project-readiness, and
linear-provider-onboarding for project write-lock coordination.
Implementation Tasks 1–3 are complete. Final review, OpenSpec archive, PR/CI, and
work-finish closeout remain. [Execution plan](../../../docs/superpowers/plans/2026-09-05-portable-workflow-bundles.md).
