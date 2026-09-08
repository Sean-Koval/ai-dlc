# Optional UI/UX workflow tasks

Current steering: product-shaping and traceability interfaces are accepted locally
at `4058b24`; the coordinator approved isolated parallel implementation. Remote
finish stays pending and no runtime dependency/completion checks are bypassed. Follow the [execution plan](../../../docs/superpowers/plans/2026-09-05-design-pm-workflow.md)
for file ownership, examples, checks and handoff. Its Task 1 covers sections 1
and 4.1; Task 2 covers section 2; Task 3 covers sections 3 and 4.2–4.4 below.
These are implementation checkboxes, not evidence that planning completed them.

## 1. Review and artifact contract

- [x] 1.1 Review the product brief, proposed rubric defaults, and capability scenarios before implementation.
- [x] 1.2 Finalize brief, rubric, evaluation, and selection templates with criterion/candidate/version identity.

## 2. Portable guidance

- [x] 2.1 Add guidance for brief-to-criteria translation with original anchored examples.
- [x] 2.2 Add generation and independent-evaluation responsibilities plus separate-session/human fallback.
- [x] 2.3 Define budget, plateau, regression, evidence, and rubric-change behavior in the iteration guidance.

## 3. Distribution and handoff

- [x] 3.1 Integrate source assets, integrity metadata, managed rendering, and project templates.
- [x] 3.2 Extend the design handoff and tool map without changing existing finish gates.
- [x] 3.3 Verify generated ownership, authored-content preservation, packaging, and continuation artifacts.

## 4. Calibration protocol and validation

- [x] 4.1 Supply an original example case set and a protocol for human calibration and held-out comparisons.
- [ ] 4.2 Verify failure/unverified/score handling through meaningful workflow scenarios; distinguish fixtures from live results.
- [ ] 4.3 Run required project checks, validate OpenSpec, and complete source review. Local required checks (1,218 tests) and strict validation (15 items) passed; independent source review remains pending.
- [ ] 4.4 Archive the implemented specification, link PR/CI evidence, and complete through the configured finish boundary.
