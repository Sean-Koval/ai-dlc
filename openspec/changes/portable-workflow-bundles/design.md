## Context

Make a replaceable workflow bundle reproducible in the project repository and discoverable to the harness using existing managed rendering.
Read [product direction](../../../docs/product-direction.md) and the [delivery architecture](../../../docs/design/framework-delivery.md).

## Goals / Non-Goals

Goal: Make a replaceable workflow bundle reproducible in the project repository and discoverable to the harness using existing managed rendering.

Excluded: No arbitrary installer/scripts, marketplace, dependency solver, new client adapter, remote auto-update, or changes to personal profile enrollment semantics.

## Decisions

First bundle format is schema=1, id, skills mapping names to relative SKILL.md paths, templates mapping names to relative Markdown paths, and files mapping every included relative path to sha256. First delivery allows regular UTF-8 Markdown only, at most 2 MiB/file and 10 MiB total; no symlinks, scripts, absolute paths, traversal, or undeclared files. Guidance remains untrusted input for the receiving harness. Add ai-dlc agents bundle import SOURCE --ref REF --id ID [--apply --expected-commit SHA]; preview can fetch to temporary storage but cannot change active files. Reuse existing Git source validation through a public shared helper while preserving profile-source tests; resolve an advertised ref to an exact commit and compare it again on apply. Apply vendors selected files plus a lock under .ai-dlc/bundles/ID. Project-only agents.bundles selects these IDs, so Git transports them between machines. Existing agents.skills remains shipped-skill selection. Resolve name collisions by refusing, never overwrite. No remote registry or automatic startup fetch. The --expected-commit flag is required for apply and must equal the previewed commit. Import operates on a bundle root containing bundle.json and its declared payload; Git metadata is excluded. References in Markdown never authorize execution. Add agents.bundles to project-only nested configuration validation; reject it in personal/machine layers in this first delivery.

### Interface contract

validate_bundle(root: Path, manifest: dict) -> dict returns a validated schema-1 manifest. resolve_bundle(source:str, ref:str, bundle_id:str, *, environ) -> candidate with resolved_commit and file hashes; it does not activate files. import_bundle(root:Path, candidate, *, apply:bool=False) -> {applied, changed, conflicts, resolved_commit}. The candidate type and cleanup lifecycle are defined in workflow_bundles.py; no active profile lock is mutated.

### Dependency contract

- component-capability-contract: consume its committed documented interfaces; do not implement an incompatible local substitute.
- connected-project-readiness: consume its committed documented interfaces; do not implement an incompatible local substitute.

## Risks / Trade-offs

- Existing configuration or content is changed accidentally → retain compatibility and refusal-path tests.
- An agent implements a neighboring ticket's responsibilities → use the explicit file/interface boundaries and dependency gate.
- Generated assets drift from source → update source, integrity metadata and generated copies together and run required checks.

## Migration Plan

Use additive defaults for existing configurations. Preview before applicable mutations; preserve original files on validation failures. Deliver changes on an independently reviewed branch. Reverting owned assets must preserve authored project content and prior provider bindings.

## Verification

- WB-01: exercise a source ref moves before apply and the corresponding expected result in the formal spec.
- WB-02: exercise an imported skill has a local edit and the corresponding expected result in the formal spec.
- WB-03: exercise a fresh checkout has no network and the corresponding expected result in the formal spec.

[Task-level instructions and acceptance example](../../../docs/superpowers/plans/2026-09-05-portable-workflow-bundles.md).
