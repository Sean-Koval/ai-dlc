## Why

Make a replaceable workflow bundle reproducible in the project repository and discoverable to the harness using existing managed rendering.
This implements the approved framework direction in [product direction](../../../../docs/product-direction.md), milestone M1.

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
Implementation Tasks 1–3 are committed, including fix commit `ca5ab0a`, with 739
focused and 1,134 full tests passing as pre-review local evidence. Final review is
not accepted. The user-authorized fix at `19809bc` carries stage identity and
expected bytes, fixes the two original reproductions, and passes 741 focused and
1,136 full tests with all five required outcomes as pre-review local evidence.
That review found a remaining verification/unlink race. The maintainer authorized
another scoped remediation and independent review on September 6. The repair
retains failed stages and reports their filenames/paths instead of deleting by
name; portable filesystem APIs do not offer an identity-conditioned unlink.
The separate successful-transaction backup deletion race remains outside this
stage repair. OpenSpec archive, PR/CI/merge, and work finish remain blocked on
whole-change acceptance. [Execution plan](../../../../docs/superpowers/plans/2026-09-05-portable-workflow-bundles.md).
