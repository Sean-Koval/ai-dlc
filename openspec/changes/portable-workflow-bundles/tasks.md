## 1. Manifest and digest validation

- [x] 1.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [x] 1.2 Implement duplicate-key-safe manifest loading plus `validate_bundle` with malformed, oversized, traversal, symlink, non-regular, extra-file, digest, duplicate name/path, exact export coverage, and portable skill-frontmatter cases. Requested/manifest ID comparison remains Task 2 behavior. Validate all assets before planning a write; imports and rendering remain Tasks 2 and 3.
- [x] 1.3 Verify focused tests and inspect scope/compatibility before committing.

## 2. Pinned import preview/apply

- [ ] 2.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [ ] 2.2 Implement portable temporary source resolution, requested/manifest ID equality, reviewed revision matching at the service boundary, the specified complete vendored lock, same-owner update guards, and rollback on partial file errors. Import must not select or render the bundle. Preserve the existing profile-source security contract when sharing helpers.
- [ ] 2.3 Verify focused tests and inspect scope/compatibility before committing.

## 3. Client and template distribution

- [ ] 3.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [ ] 3.2 Extend owned skill/template/index rendering, project-only config validation, and bundle-aware readiness; demonstrate one external Markdown bundle in a fresh checkout with source access disabled.
- [ ] 3.3 Verify focused tests and inspect scope/compatibility before committing.

## 4. Review and finish

- [ ] 4.1 Run required project checks and strict OpenSpec validation.
- [ ] 4.2 Complete source review, archive the delivered change, link PR/CI evidence, and finish through the configured workflow.

[Detailed plan](../../../docs/superpowers/plans/2026-09-05-portable-workflow-bundles.md).
