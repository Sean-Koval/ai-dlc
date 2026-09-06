# Framework Delivery Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans with one ticket's linked plan at a time. Use superpowers:subagent-driven-development only when delegation is authorized. Checkboxes record delivered work, not planning completion.

**Goal:** Deliver the approved portable development framework with connected setup, replaceable tools, product-to-delivery guidance, and measured qualification.

**Architecture:** Retain current Python services and native tools. Add a small component/readiness boundary, strengthen product/spec handoffs, and distribute optional workflows through managed assets. Each behavior ticket owns a separate OpenSpec change.

**Tech Stack:** Python 3.12, uv/mise/native package managers, OpenSpec, Markdown, current provider adapters, and Codex/Claude managed assets.

**Spec:** [Product direction](../../product-direction.md), [delivery architecture](../../design/framework-delivery.md), and each ticket's formal change below.

## Global constraints

- Existing schema 4, profile ownership, credential isolation, authored-content preservation, and completion gates remain intact.
- The original planning delivery contained no runtime implementation; the
  current repository now includes completed implementation through SAN-11 and
  committed SAN-12 Tasks 1–3. The renewed scoped remediation retains failed
  stages and reports recovery residue. SAN-12 final review still requires
  resolution of the separate successful-transaction backup deletion race.
- Native macOS arm64 and Ubuntu 24.04 arm64 devcontainer are the initial qualification targets; client/hosted claims require actual evidence.
- UI/UX is optional within product development. Specification is observable behavior; ticket is a deliverable slice; task is a smaller implementation step.
- Paid experiments require a separately declared budget, and human ratings require humans.
- Before ticket work, confirm its predecessors are Done in Linear. Continue
  active work on its bound `codex/<work-id>` branch; start later tickets from
  current main only when their dependencies are complete. Run source bootstrap
  and required project checks as described in AGENTS.md.
- Use one reviewed branch per ticket, with independently finishable specifications. Do not implement dependency APIs by guessing.
- Future Work.depends_on/requirements fields are introduced only by the traceability ticket; until then use this graph and native tracker relations.

## Ticket order and plans

| Work ID | Status snapshot | Milestone | Prerequisites | Plan |
| --- | --- | --- | --- | --- |
| `component-capability-contract` | Done | M1 | None | [Execute](2026-09-05-component-capability-contract.md) |
| `connected-project-readiness` | Done | M1 | component-capability-contract | [Execute](2026-09-05-connected-project-readiness.md) |
| `linear-provider-onboarding` | Done | M1 | component-capability-contract | [Execute](2026-09-05-linear-provider-onboarding.md) |
| `portable-workflow-bundles` | In Progress — Tasks 1–3 committed; review blocked after authorized remediation | M1 | component-capability-contract, connected-project-readiness, linear-provider-onboarding | [Execute](2026-09-05-portable-workflow-bundles.md) |
| `product-shaping-workflow` | Backlog | M2 | None | [Execute](2026-09-05-product-shaping-workflow.md) |
| `spec-delivery-traceability` | Backlog | M2 | product-shaping-workflow | [Execute](2026-09-05-spec-delivery-traceability.md) |
| `design-pm-workflow` | Backlog | M2 | product-shaping-workflow, spec-delivery-traceability | [Execute](2026-09-05-design-pm-workflow.md) |
| `framework-qualification` | Backlog | M3 | connected-project-readiness, linear-provider-onboarding, portable-workflow-bundles, spec-delivery-traceability | [Execute](2026-09-05-framework-qualification.md) |
| `workflow-quality-calibration` | Backlog | M3 | product-shaping-workflow, spec-delivery-traceability | [Execute](2026-09-05-workflow-quality-calibration.md) |
| `design-pm-calibration` | Backlog | M3 | design-pm-workflow | [Execute](2026-09-05-design-pm-calibration.md) |

Resolve the remaining backup deletion boundary and finish
portable-workflow-bundles (SAN-12), then continue with
product-shaping-workflow (SAN-13). M1 and M2 are outcomes, not a requirement to
serialize otherwise independent work.

## Milestone exit criteria

### M1: Connected setup and replaceable guidance

- [x] Explicit role selection resolves tool modules, configuration requirements, and provider guidance.
- [x] Root-aware setup can prepare the selected tools; offline readiness names concrete gaps without false qualification claims.
- [x] Linear discovery and local configuration need no manual UUID hunting or secret persistence.
- [ ] A pinned external Markdown workflow bundle is usable offline from a fresh checkout and respects owned-content updates.

### M2: Product-to-delivery workflow

- [ ] Worked greenfield and brownfield examples produce evidence-based outcomes, scope, requirement IDs, and proceed/investigate/stop decisions.
- [ ] Behavioral specifications, deliverable tickets, dependencies, and verification have explicit links.
- [ ] A changed interface can opt into the UI/UX workflow while non-UI work retains appropriate verification.
- [ ] A small change can use a small artifact set without bypassing applicable project gates.

### M3: Observed qualification and workflow quality

- [ ] Both initial live environments demonstrate repeat setup and continued work with equivalent portable choices.
- [ ] Disposable Linear/GitHub Issues cycles demonstrate provider substitution and stable previous bindings.
- [ ] Human-grounded product/delivery and UI evaluations report actual results, disagreement, cost, and limitations.
- [ ] Existing v4 release gates are updated only with matching evidence; no test category substitutes for another.

## Per-ticket execution sequence

1. Read the work record, linked plan, complete OpenSpec change when required, and predecessor interfaces.
2. Check actual dependency tracker state/evidence; choose a ready ticket.
3. Link `codex/<work-id>` with `ai-dlc work link <work-id> branch codex/<work-id>`, then run `ai-dlc work start <work-id>`. Do not execute another ticket's scope.
4. Follow the plan's focused regression → implementation → verification → commit steps.
5. Review against exclusions and requirement coverage, then run required checks.
6. For behavior tickets, validate and archive the completed OpenSpec change and update its work reference.
7. Link reviewed PR and merged-revision evidence; finish through the existing service.
8. Use the [handoff checklist](../../handoffs/framework-delivery.md) for continuation.

## Review of this planning delivery

The planning ticket covers documents, specs, plans, source/generated handbook consistency,
and synchronized backlog metadata. It must not close implementation tickets.
Validation for this branch includes all seven active new capability changes, local
link/reference checks, work-record parsing, dependency-cycle checks, and the required
project suite. The original v4 change remains active with its unmet release tasks.
