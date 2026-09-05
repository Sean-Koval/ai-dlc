## Why

AI-DLC equips harnesses with portable development tools and guidance, but its
design handoff lacks a repeatable way to turn subjective goals into observable
quality criteria. Developers need a reusable brief, evaluation contract, and
revision workflow that can travel with the project between machines and harnesses.

## What Changes

- Add portable Design PM guidance and templates for briefs, rubrics, evidence,
  independent review, revision budgets, and candidate selection.
- Integrate these assets with existing skill distribution and generated projects.
- Provide original examples that distinguish observed behavior, subjective
  judgment, missing evidence, and human decisions.
- Preserve direct use of installed design/browser tools and existing completion
  gates; introduce no required orchestration service or new CLI command.

This is a planned optional UI/UX workflow within milestone M2. Dependencies are
product-shaping-workflow and spec-delivery-traceability. It does not define the
overall framework direction. No implementation or live evaluation is complete.

## Capabilities

### New Capabilities

- `design-pm`: portable design evaluation contracts and evidence-preserving iteration.

### Modified Capabilities

None. Existing portable enrollment and completion requirements remain unchanged.

## Impact

Expected surfaces: `agents/skills/`, `agents/templates/`, skill integrity metadata,
generated client assets, `project-templates/`, design workflow documentation, and
generation/packaging tests. Additional clients require separate qualification.

Rationale and proposed example rubric: [Design PM brief](../../../docs/design/design-pm.md).
Work: [design-pm-workflow](../../../.ai-dlc/work/design-pm-workflow.toml).
Empirical calibration is a separate [work item](../../../.ai-dlc/work/design-pm-calibration.toml).
