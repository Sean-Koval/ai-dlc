## Context

Give an executing agent an unambiguous connection from outcome to behavioral scenario, ticket, implementation step, and verification evidence.
Read [product direction](../../../docs/product-direction.md) and the [delivery architecture](../../../docs/design/framework-delivery.md).

## Goals / Non-Goals

Goal: Give an executing agent an unambiguous connection from outcome to behavioral scenario, ticket, implementation step, and verification evidence.

Excluded: No automatic scope approval, duplicate spec store, spec-to-one-checkbox-ticket mapping, remote priority inference, or weakened finish gates.

## Decisions

New work records list dependency work IDs, requirement IDs, exact artifact references, and acceptance/verification text. Validate missing referenced local records, self-dependency, cycles, unsafe IDs, and absent local artifacts before publication. Dependency validation verifies graph integrity; it does not claim dependencies completed. work start checks dependency tracker state and fails explicitly on unfinished or unavailable dependencies; a terminal cancelled/duplicate item does not satisfy a completion dependency. Existing records with empty lists keep their current behavior. The native publish body includes scope, requirements, dependencies, artifacts, and acceptance plus the unchanged correlation marker. Re-publishing an already linked item remains idempotent and does not silently overwrite authored remote descriptions. Spec guidance creates one independently finishable OpenSpec change per behavior ticket; OpenSpec tasks are steps inside that ticket, not one ticket per checkbox. A shared parent epic has no completion gate over child specs.

### Interface contract

Add optional Work fields depends_on: list[str]=[] and requirements: list[str]=[]. Add validate_work_graph(records:dict[str,dict])->list[str] and render_ticket_body(work:dict)->str in traceability.py. Requirements are stable brief/spec requirement identifiers, not duplicated spec prose. Add ai-dlc work validate WORK_ID --root PATH (read-only, 0 valid/1 invalid). No automated interpretation of arbitrary natural-language specifications.

### Dependency contract

- product-shaping-workflow: consume its committed documented interfaces; do not implement an incompatible local substitute.

## Risks / Trade-offs

- Existing configuration or content is changed accidentally → retain compatibility and refusal-path tests.
- An agent implements a neighboring ticket's responsibilities → use the explicit file/interface boundaries and dependency gate.
- Generated assets drift from source → update source, integrity metadata and generated copies together and run required checks.

## Migration Plan

Use additive defaults for existing configurations. Preview before applicable mutations; preserve original files on validation failures. Deliver changes on an independently reviewed branch. Reverting owned assets must preserve authored project content and prior provider bindings.

## Verification

- TR-01: exercise a feature is decomposed and the corresponding expected result in the formal spec.
- TR-02: exercise a ticket depends on itself and the corresponding expected result in the formal spec.
- TR-03: exercise a published item is retried and the corresponding expected result in the formal spec.

[Task-level instructions and acceptance example](../../../docs/superpowers/plans/2026-09-05-spec-delivery-traceability.md).
