## 1. Pure graph validation and ticket rendering

- [ ] 1.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [ ] 1.2 Implement validate_work_graph and render_ticket_body with missing ID, self/cycle, stable order and rich body cases. Preserve correlation values. Task 2 owns optional Work fields, filesystem artifact checks and mutation ordering; the pure graph function does not inspect files or services.
- [ ] 1.3 Verify focused tests and inspect scope/compatibility before committing.

## 2. Workflow integration

- [ ] 2.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [ ] 2.2 Validate before mutation, expose work validate, check dependency completion before branch/start effects, and render richer descriptions on first create only.
- [ ] 2.3 Verify focused tests and inspect scope/compatibility before committing.

## 3. Spec and task handoff guidance

- [ ] 3.1 Define and run the focused acceptance/refusal cases in the execution plan.
- [ ] 3.2 Update skill/template examples using PS requirement IDs; show an independently finishable change and a no-spec verification item; regenerate owned copies.
- [ ] 3.3 Verify focused tests and inspect scope/compatibility before committing.

## 4. Review and finish

- [ ] 4.1 Run required project checks and strict OpenSpec validation.
- [ ] 4.2 Complete source review, archive the delivered change, link PR/CI evidence, and finish through the configured workflow.

[Detailed plan](../../../docs/superpowers/plans/2026-09-05-spec-delivery-traceability.md).
