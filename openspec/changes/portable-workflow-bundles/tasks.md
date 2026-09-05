## 1. Manifest and digest validation

- [ ] 1.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [ ] 1.2 Implement validate_bundle with malformed, oversized, traversal, symlink, extra-file, digest mismatch, and duplicate-name cases. Validate all assets before planning a write; imports and rendering remain Tasks 2 and 3.
- [ ] 1.3 Verify focused tests and inspect scope/compatibility before committing.

## 2. Pinned import preview/apply

- [ ] 2.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [ ] 2.2 Implement temporary source resolution, reviewed revision matching, vendored lock, and rollback on partial file errors. Preserve the existing profile-source security contract when sharing helpers.
- [ ] 2.3 Verify focused tests and inspect scope/compatibility before committing.

## 3. Client and template distribution

- [ ] 3.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [ ] 3.2 Extend owned skill/template rendering and project-only config validation; demonstrate one external Markdown bundle in a fresh checkout, offline.
- [ ] 3.3 Verify focused tests and inspect scope/compatibility before committing.

## 4. Review and finish

- [ ] 4.1 Run required project checks and strict OpenSpec validation.
- [ ] 4.2 Complete source review, archive the delivered change, link PR/CI evidence, and finish through the configured workflow.

[Detailed plan](../../../docs/superpowers/plans/2026-09-05-portable-workflow-bundles.md).
