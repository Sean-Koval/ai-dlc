## 1. Paginated discovery

- [x] 1.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [x] 1.2 Implement discover_linear with injected httpx responses covering multiple teams, duplicate names, two started states, pagination, authorization failure, and incomplete result refusal. Expose no mutations or CLI apply in this task.
- [x] 1.3 Verify focused tests and inspect scope/compatibility before committing.

## 2. Selection and guarded local write

- [ ] 2.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [ ] 2.2 Implement plan_linear_connection and apply_linear_connection: validate selection membership/types and config digest, preserve comments and unrelated sections, write atomically, and prove invalid/stale selections write nothing. Task 3 owns CLI wiring and fresh remote membership checks.
- [ ] 2.3 Verify focused tests and inspect scope/compatibility before committing.

## 3. CLI and guarded apply

- [ ] 3.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [ ] 3.2 Implement provider connect preview/apply, credential-redacted errors, and binding-drift refusal. Add a sandbox read-only walkthrough procedure.
- [ ] 3.3 Verify focused tests and inspect scope/compatibility before committing.

## 4. Review and finish

- [ ] 4.1 Run required project checks and strict OpenSpec validation.
- [ ] 4.2 Complete source review, archive the delivered change, link PR/CI evidence, and finish through the configured workflow.

[Detailed plan](../../../docs/superpowers/plans/2026-09-05-linear-provider-onboarding.md).
