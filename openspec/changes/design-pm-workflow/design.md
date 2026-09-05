## Context

The [product brief](../../../docs/design/design-pm.md) defines the opportunity and
example rubric. This is an optional M2 workflow, after product shaping and delivery
traceability, within the [framework direction](../../../docs/product-direction.md). AI-DLC already
distributes skills/templates and preserves generated ownership. Its existing
skill evaluation protocol is pending and evaluates different behaviors.

## Goals / Non-Goals

Goals: give a harness usable brief/rubric/review instructions, durable continuation
artifacts, explicit evidence rules, and a bounded revision pattern.

Non-goals: a mandatory agent runtime, UI implementation, automatic taste judgment,
new finish gates, forced model selection, and unverified client integrations.

## Decisions

1. Package Markdown templates and skill guidance through current asset mechanisms.
   This reaches the harness in its existing environment. A dedicated service is
   unnecessary for the initial workflow; automation can follow observed need.
2. Extend existing product/discovery/design handoffs instead of introducing a second
   PRD lifecycle. OpenSpec owns behavioral contracts, the brief owns rationale,
   and iteration reports own observations. Link these artifacts.
3. Separate required checks from rated criteria. Required failures and missing
   evidence block acceptance regardless of any optional aggregate score.
4. Keep evaluation inputs and candidate identity explicit. A separate session or
   human can provide independent review where native delegation is absent.
5. Ship original examples and a calibration protocol; use a separately budgeted
   experiment to determine actual quality lift. Do not reuse the pending generic
   skill evaluation budget without an explicit change to that experiment.

## Risks / Trade-offs

- Evaluator preference becomes a hidden product requirement → tie criteria to the
  brief, preserve human disagreements, and version changes.
- Scores reward complexity → include task fit, regression checks, and explicit budgets.
- Artifacts become ceremony → create them only for work needing design evaluation;
  keep a single contract with linked evidence rather than duplicated documents.
- Cross-client behavior differs → qualify each client separately and report absent
  capabilities without pretending to have observed the interface.

## Migration Plan

Add source skills/templates and update their managed/generated counterparts using
the existing renderer. Extend the project design handoff with links to the new
optional workflow. Verify packaging and owned-update/conflict behavior. Roll back
by reverting the asset addition through the same ownership mechanism; preserve
project-authored briefs and evidence.

## Execution contract

Implement design-brief and design-evaluate using Markdown artifacts and the
selected existing generation tools. Consume the shaped product brief and delivery
slice; preserve their requirement IDs. The [execution plan](../../../docs/superpowers/plans/2026-09-05-design-pm-workflow.md)
defines exact files, responsibilities, sample defaults, and verification. Human
calibration remains separate work; project-specific references and budgets are
inputs to each evaluation rather than global framework requirements.
