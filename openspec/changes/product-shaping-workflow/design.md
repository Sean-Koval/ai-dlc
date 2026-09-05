## Context

Give agents concrete guidance and examples for choosing worthwhile product increments before writing specifications or code.
Read [product direction](../../../docs/product-direction.md) and the [delivery architecture](../../../docs/design/framework-delivery.md).

## Goals / Non-Goals

Goal: Give agents concrete guidance and examples for choosing worthwhile product increments before writing specifications or code.

Excluded: No invented interviews or user approval, automatic ticket publication during discovery, mandatory UI work, replacement specification system, or broad autonomous feature expansion.

## Decisions

Reuse existing discovery/PRD/inbox skills; do not create a competing PM lifecycle. Greenfield compares at least two feasible approaches plus doing nothing when meaningful. Brownfield records actual behavior, constraints, affected users, compatibility, and rollback needs. Separate user evidence from model hypotheses. Make priority a reasoned judgment using user impact, confidence in evidence, effort, and dependencies without fabricated numeric precision. UI exploration is optional and routes to design-pm-workflow only when the slice changes an interface. Small work can use a single brief; no mandatory PRD/design/ticket duplication.

### Interface contract

The product brief is Markdown with stable sections: Audience and problem; Evidence and assumptions; Current behavior (brownfield); Options and trade-offs; Selected outcome; Scope and exclusions; Success evidence; Next slice; Unresolved decisions. Requirement IDs use RQ-001 style within the brief; one canonical brief owns those IDs. Output ends with proceed, investigate, or stop plus reasons, not an invented approval.

### Dependency contract

No feature dependency. Begin after the planning documentation is integrated.

## Risks / Trade-offs

- Existing configuration or content is changed accidentally → retain compatibility and refusal-path tests.
- An agent implements a neighboring ticket's responsibilities → use the explicit file/interface boundaries and dependency gate.
- Generated assets drift from source → update source, integrity metadata and generated copies together and run required checks.

## Migration Plan

Use additive defaults for existing configurations. Preview before applicable mutations; preserve original files on validation failures. Deliver changes on an independently reviewed branch. Reverting owned assets must preserve authored project content and prior provider bindings.

## Verification

- PS-01: exercise a request contains only a feature idea and the corresponding expected result in the formal spec.
- PS-02: exercise an existing workflow is changed and the corresponding expected result in the formal spec.
- PS-03: exercise evidence is insufficient and the corresponding expected result in the formal spec.

[Task-level instructions and acceptance example](../../../docs/superpowers/plans/2026-09-05-product-shaping-workflow.md).
