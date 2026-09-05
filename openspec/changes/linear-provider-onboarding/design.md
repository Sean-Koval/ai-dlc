## Context

Replace manual team/status UUID hunting with explicit, read-only discovery and a reviewed local configuration update.
Read [product direction](../../../docs/product-direction.md) and the [delivery architecture](../../../docs/design/framework-delivery.md).

## Goals / Non-Goals

Goal: Replace manual team/status UUID hunting with explicit, read-only discovery and a reviewed local configuration update.

Excluded: No API-key creation, Linear Project creation, issue mutation, organization switching, or automatic rebind. Use existing sandbox only for authorized live reads.

## Decisions

Add ai-dlc provider connect PROVIDER --root PATH. Without selection flags it prints complete discovery and exits without writes. Preview flags are --organization UUID --team UUID --in-progress UUID --closed UUID; --apply additionally writes local shared non-secret mappings. Use existing token_env; do not create or rotate keys. Validate selected team belongs to the selected organization result, started/completed state types and team membership. Multiple states are always listed; never infer In Progress from first started state. Paginate all selected discovery collections or fail incomplete. Preserve unrelated TOML content using a reviewed TOML editing approach; tests must assert comments and unrelated values survive. Refuse changed existing mappings when local work is already bound; point to explicit rebind. Preview can save its non-secret plan with --plan-file PATH under .ai-dlc/local. Apply consumes --plan-file PATH with --apply, revalidates selections against fresh discovery, and checks before_digest immediately before the atomic write; it never silently recomputes a different approved plan.

### Interface contract

discover_linear(settings: dict, *, environ: Mapping[str,str], client) -> dict returns {organization:{id,name,urlKey}, teams:[{id,name,key,states:[{id,name,type}]}]}. plan_linear_connection(config:dict, discovery:dict, selection:dict) -> dict returns {provider, before_digest, selected, patch}; selection requires organization_id, team_id, in_progress, closed. apply_linear_connection(path:Path, plan:dict) verifies the before digest and atomically replaces only selected provider settings.

### Dependency contract

- component-capability-contract: consume its committed documented interfaces; do not implement an incompatible local substitute.

## Risks / Trade-offs

- Existing configuration or content is changed accidentally → retain compatibility and refusal-path tests.
- An agent implements a neighboring ticket's responsibilities → use the explicit file/interface boundaries and dependency gate.
- Generated assets drift from source → update source, integrity metadata and generated copies together and run required checks.

## Migration Plan

Use additive defaults for existing configurations. Preview before applicable mutations; preserve original files on validation failures. Deliver changes on an independently reviewed branch. Reverting owned assets must preserve authored project content and prior provider bindings.

## Verification

- LN-01: exercise two started states exist and the corresponding expected result in the formal spec.
- LN-02: exercise configuration changes after preview and the corresponding expected result in the formal spec.
- LN-03: exercise an existing binding would change and the corresponding expected result in the formal spec.

[Task-level instructions and acceptance example](../../../docs/superpowers/plans/2026-09-05-linear-provider-onboarding.md).
