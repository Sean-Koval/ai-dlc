## Context

Resolve explicitly selected provider roles into a deterministic, versioned description of required tools, guidance, configuration, and checks.
Read [product direction](../../../docs/product-direction.md) and the [delivery architecture](../../../docs/design/framework-delivery.md).

## Goals / Non-Goals

Goal: Resolve explicitly selected provider roles into a deterministic, versioned description of required tools, guidance, configuration, and checks.

Excluded: No package registry, remote downloads, new provider operations, model selection, or changes to finish gates.

## Decisions

Component schema 1 contains id, roles, modules, guidance, required_config. Modules name existing entries in modules/catalog.toml; guidance is a list of repository/package-relative Markdown paths. Built-ins are indexed by provider kind. An optional providers.<id>.component overrides the component ID. Optional providers.<id>.component_manifest and component_manifest_sha256 select a checked-in JSON manifest verified before parsing. Unknown fields, duplicate IDs, unsafe paths, missing hashes, unknown modules, and incompatible roles fail validation. No manifest command strings or installers are executed. Native adapters remain in the existing provider registry.

### Interface contract

resolve_components(config: dict, catalog: dict) -> dict returns {schema: 1, components: [{id, provider, role, modules, guidance, required_config}], unresolved: [{provider, role, reason}]}. Lists are sorted by stable IDs. This function is pure and accepts only explicitly selected roles; the caller excludes compatibility-only base defaults.

### Dependency contract

No feature dependency. Begin after the planning documentation is integrated.

## Risks / Trade-offs

- Existing configuration or content is changed accidentally → retain compatibility and refusal-path tests.
- An agent implements a neighboring ticket's responsibilities → use the explicit file/interface boundaries and dependency gate.
- Generated assets drift from source → update source, integrity metadata and generated copies together and run required checks.

## Migration Plan

Use additive defaults for existing configurations. Preview before applicable mutations; preserve original files on validation failures. Deliver changes on an independently reviewed branch. Reverting owned assets must preserve authored project content and prior provider bindings.

## Verification

- CC-01: exercise openspec is selected without its module and the corresponding expected result in the formal spec.
- CC-02: exercise custom metadata is altered and the corresponding expected result in the formal spec.
- CC-03: exercise an alternative tracker is selected and the corresponding expected result in the formal spec.

[Task-level instructions and acceptance example](../../../docs/superpowers/plans/2026-09-05-component-capability-contract.md).
