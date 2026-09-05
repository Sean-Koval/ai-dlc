## Context

Join selected provider requirements with machine provisioning and expose actionable project readiness without confusing it with release certification.
Read [product direction](../../../docs/product-direction.md) and the [delivery architecture](../../../docs/design/framework-delivery.md).

## Goals / Non-Goals

Goal: Join selected provider requirements with machine provisioning and expose actionable project readiness without confusing it with release certification.

Excluded: No credential auto-loading, automatic account choice, new client support claim, hosted control plane, or weakening of existing doctor/finish behavior.

## Decisions

Add ai-dlc project readiness --root PATH (read-only; exit 0 only when required checks are ready, else 1). Dimensions are tool, configuration, credential, guidance, and provider-health. Use catalog verify commands through a bounded injected probe; no installs/network for plain readiness, provider-health remains unverified unless existing explicit health inspection was requested through doctor. Provider-health is informational in offline readiness. Extend setup plan/apply and machine plan/apply with optional --root; root-aware planning unions declared modules with resolved component modules without editing the profile. Apply follows the existing explicit mutation command. Guidance readiness checks that the selected harness receives an index pointing to real configured-provider instructions. Existing root/machine doctor readiness contract is preserved, with the richer project report added under project_readiness.

### Interface contract

inspect_readiness(root: Path, config: dict, *, environ: Mapping[str,str], probe: Callable[[list[str]],dict]) -> dict returns {schema:1, ready:bool, checks:[{component, dimension, status, reason, next_action}], qualification:'not-assessed'}. status is ready, missing, blocked, or unverified. Extend MachineManager.plan/apply with optional root: Path | None = None; omitted root retains current behavior.

### Dependency contract

- component-capability-contract: consume its committed documented interfaces; do not implement an incompatible local substitute.

## Risks / Trade-offs

- Existing configuration or content is changed accidentally → retain compatibility and refusal-path tests.
- An agent implements a neighboring ticket's responsibilities → use the explicit file/interface boundaries and dependency gate.
- Generated assets drift from source → update source, integrity metadata and generated copies together and run required checks.

## Migration Plan

Use additive defaults for existing configurations. Preview before applicable mutations; preserve original files on validation failures. Deliver changes on an independently reviewed branch. Reverting owned assets must preserve authored project content and prior provider bindings.

## Verification

- RD-01: exercise a project requires an absent tool and the corresponding expected result in the formal spec.
- RD-02: exercise tool installation alone is insufficient and the corresponding expected result in the formal spec.
- RD-03: exercise a second environment is headless and the corresponding expected result in the formal spec.

[Task-level instructions and acceptance example](../../../docs/superpowers/plans/2026-09-05-connected-project-readiness.md).
