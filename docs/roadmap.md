# AI-DLC roadmap

Updated: 2026-09-05. Linear owns priority and status. This document owns the
delivery sequence; [product direction](product-direction.md) owns the intended
outcomes. The capabilities below are planned, not shipped.

## Direction and current baseline

AI-DLC prepares portable environments and connects replaceable tools, guidance,
artifacts, and quality workflows. The harness performs development using native
tools or AI-DLC services as appropriate. UI/UX is an optional workflow, not the
framework's organizing purpose.

The current Python implementation supplies bootstrap/enrollment, scoped
configuration, provider adapters, managed assets, work records, and finish gates.
The next work connects those foundations and improves product-to-delivery
guidance. See [current architecture](architecture.md) and
[planned contracts](design/framework-delivery.md) for the distinction.

## Dependency-ordered delivery

Each row is an independently reviewed ticket with an execution plan. Plan tasks
are steps inside that ticket, not additional disconnected issues. All ten items
were published to the Sandbox-aidlc team; SAN-6 and SAN-7 were revised in place.

| Ticket | Outcome | Must follow | Execution plan |
| --- | --- | --- | --- |
| [SAN-9](https://linear.app/sandbox-aidlc/issue/SAN-9/connect-provider-roles-to-tool-installation-and-harness-guidance) | M1: Connect provider roles to tool installation and harness guidance | Planning integrated | [component-capability-contract](superpowers/plans/2026-09-05-component-capability-contract.md) |
| [SAN-10](https://linear.app/sandbox-aidlc/issue/SAN-10/make-selected-project-tools-and-guidance-ready-across-machines) | M1: Make selected project tools and guidance ready across machines | SAN-9 | [connected-project-readiness](superpowers/plans/2026-09-05-connected-project-readiness.md) |
| [SAN-11](https://linear.app/sandbox-aidlc/issue/SAN-11/discover-and-safely-configure-a-projects-linear-connection) | M1: Discover and safely configure a project's Linear connection | SAN-9 | [linear-provider-onboarding](superpowers/plans/2026-09-05-linear-provider-onboarding.md) |
| [SAN-12](https://linear.app/sandbox-aidlc/issue/SAN-12/import-pinned-workflow-guidance-and-expose-it-to-supported-harnesses) | M1: Import pinned workflow guidance and expose it to supported harnesses | SAN-9, SAN-10 | [portable-workflow-bundles](superpowers/plans/2026-09-05-portable-workflow-bundles.md) |
| [SAN-13](https://linear.app/sandbox-aidlc/issue/SAN-13/guide-product-discovery-and-feature-selection-for-new-and-existing) | M2: Guide product discovery and feature selection for new and existing products | Planning integrated | [product-shaping-workflow](superpowers/plans/2026-09-05-product-shaping-workflow.md) |
| [SAN-14](https://linear.app/sandbox-aidlc/issue/SAN-14/carry-product-requirements-into-independently-deliverable) | M2: Carry product requirements into independently deliverable specifications and tickets | SAN-13 | [spec-delivery-traceability](superpowers/plans/2026-09-05-spec-delivery-traceability.md) |
| [SAN-6](https://linear.app/sandbox-aidlc/issue/SAN-6/add-optional-uiux-design-generation-and-evaluation-workflow) | M2: Add optional UI/UX design generation and evaluation workflow | SAN-13, SAN-14 | [design-pm-workflow](superpowers/plans/2026-09-05-design-pm-workflow.md) |
| [SAN-15](https://linear.app/sandbox-aidlc/issue/SAN-15/qualify-portable-setup-provider-replacement-and-development-handoffs) | M3: Qualify portable setup, provider replacement, and development handoffs | SAN-10, SAN-11, SAN-12, SAN-14 | [framework-qualification](superpowers/plans/2026-09-05-framework-qualification.md) |
| [SAN-16](https://linear.app/sandbox-aidlc/issue/SAN-16/evaluate-product-shaping-and-delivery-guidance-against-baseline) | M3: Evaluate product shaping and delivery guidance against baseline behavior | SAN-13, SAN-14 | [workflow-quality-calibration](superpowers/plans/2026-09-05-workflow-quality-calibration.md) |
| [SAN-7](https://linear.app/sandbox-aidlc/issue/SAN-7/calibrate-uiux-evaluation-and-measure-its-incremental-value) | M3: Calibrate UI/UX evaluation and measure its incremental value | SAN-6 | [design-pm-calibration](superpowers/plans/2026-09-05-design-pm-calibration.md) |

### M1: Connected setup and replaceable guidance

A selected provider connects to its tools, local configuration requirements,
instructions, and honest readiness checks. Linear setup no longer requires
manually copying UUIDs. Reviewed Markdown workflows can be pinned and distributed
without creating an arbitrary-code package system.

### M2: Product decisions become deliverable work

Greenfield and brownfield examples guide evidence gathering, alternatives,
feature selection, scope, and success criteria. Product requirement IDs flow
into behavioral specifications and independently deliverable tickets. UI work
can add a brief, rubric, generation, independent evaluation, and bounded revision.

### M3: Prove portability and quality

Observe real setup and continuation on the named native/container targets, test
replacement of a tracker in isolated destinations, and measure product/design
guidance against baselines. Missing human ratings, experiment budgets, or live
environments leave the affected evidence pending; they do not block unrelated
preparation or become invented results.

## Start and completion rules

Default first implementation: [SAN-9](https://linear.app/sandbox-aidlc/issue/SAN-9/connect-provider-roles-to-tool-installation-and-harness-guidance).
[SAN-13](https://linear.app/sandbox-aidlc/issue/SAN-13/guide-product-discovery-and-feature-selection-for-new-and-existing)
is independently ready for a product-guidance owner. Integrate this planning
branch before starting feature branches. Milestone labels do not serialize
otherwise independent work.

Seven behavior tickets have separate OpenSpec changes; the three M3 tickets
verify predecessor behavior and do not invent new specifications. Each plan
lists files, interfaces, acceptance, refusal cases, tests, exclusions, and
handoff requirements. Implement and finish one selected ticket at a time.

Dependencies are recorded as native Linear blocking relationships and in the
[machine-readable delivery index](planning/delivery-index.json). The current
Work schema does not yet support dependency fields: check the graph manually
until SAN-14 implements that behavior.

The [master plan](superpowers/plans/2026-09-05-framework-delivery.md) defines
milestone exits. The [executor handoff](handoffs/framework-delivery.md) is the
starting document for an agent without this conversation.
[SAN-8: planning delivery](https://linear.app/sandbox-aidlc/issue/SAN-8/document-and-sequence-the-portable-framework-delivery-roadmap)
tracks documentation/review only; its completion must not close these features.

## Retained v4 release obligations

The implementation PR is merged, but
[portable-development-v4](../openspec/changes/portable-development-v4/tasks.md)
remains active with four unfinished release tasks. Do not create replacement
claims or archive it merely because this roadmap exists.

- Clean-machine, container, and hosted-client walkthroughs.
- Full live provider mutation conformance under enforced isolation.
- Behavioral evaluations already declared in `agents/evaluation.toml`.
- Verified release artifacts and release bootstrap manifest.

[Release verification](release-verification.md) records actual evidence. M3
evidence can satisfy an existing gate only when its scope matches. New product
and UI comparisons do not consume or redefine existing evaluation budgets.

## Explicitly deferred

Additional harness/hosted adapters, executable workflow packages, knowledge
onboarding, automatic Linear Project assignment, existing-work attachment, and
release publication need separately scoped work. They are not hidden acceptance
requirements for these ten tickets.
