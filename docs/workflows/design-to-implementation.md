# Design to implementation

This guide defines the evidence passed from product and technical design into
implementation. A design explains intent, journeys, constraints, boundaries,
and decisions. It does not duplicate a PRD, formal specification, tracker, or
implementation diff.

[Back to the workflow map](../development-workflow.md)

## The handoff contract

An implementation-ready design answers the following questions or links to the
artifact that does:

| Area | Required evidence |
| --- | --- |
| Identity | Work ID, title, owner, status, and links to tracker and requirements |
| Outcome | Audience, problem, measurable outcome, scope, and explicit non-goals |
| Journey | Entry point, main path, state transitions, permissions, errors, empty/loading states, and accessibility needs |
| System | Deployment and module boundaries, dependency direction, interfaces, data ownership, and failure behavior |
| Decisions | Alternatives considered, selected approach, consequences, and linked ADRs for consequential choices |
| Behavior | Acceptance criteria and links to the current formal specification when required |
| Verification | Acceptance, regression, integration, migration, security, and operational test strategy as applicable |
| Delivery | Incremental slices, compatibility constraints, rollout, observability, recovery, and rollback |
| Traceability | Work record, specification, decisions, branch, pull request, and runbook links as they become available |

The source templates live at `agents/templates/design.md`,
`agents/templates/adr.md`, and `agents/templates/runbook.md`; generated projects
receive them under `docs/templates/`. Update `docs/architecture.md` only when
the durable system view changes.

## Handoff flow

```mermaid
flowchart TD
    R[Reviewed requirements] --> D[Design document]
    D --> A[Architecture and ADR updates]
    A --> N{Material behavior needs formal specification?}
    N -->|Yes| S[Current formal specification and scenarios]
    N -->|No| E[Recorded no-spec decision]
    S --> W[Reviewed AI-DLC work record]
    E --> W
    W --> P[Implementation slices and test plan]
    P --> B[Bound work branch]
    B --> PR[Code, tests, docs, pull request]
```


The work record is the traceability bridge. It binds approved scope and remote
artifacts before implementation mutates the tracker or creates branch state.
It should link durable sources rather than paste their contents.

## Greenfield handoff

For a new application, design begins with the first deployable boundary and
one end-to-end user outcome. Define the minimum architecture needed for that
slice, then identify which interfaces are intentionally stable and which are
still internal. Avoid designing hypothetical services, extension systems, or
configuration until a requirement needs them.

The first slice must leave a reproducible setup, lockfile, baseline checks, and
one observable behavior. Its tests prove both the language/toolchain baseline
and the user outcome.

## Brownfield handoff

For an existing application, design begins with evidence about current
behavior. List affected interfaces, callers, data, operational procedures, and
compatibility promises. Characterization tests protect important existing
contracts. The design states how each slice moves from the current state to the
target state and how to recover if the transition fails.

Do not use a broad rewrite as the handoff unit when an incremental change can
be reviewed, verified, and rolled back independently.

## Implementation expectations

Before coding, an implementer should be able to map each acceptance criterion
or required scenario to a planned slice and verification method. During
implementation:

- work only on the bound branch and within reviewed scope;
- use tests to drive new behavior and reproduce bugs;
- preserve unrelated user changes and existing contracts;
- update design, decisions, architecture, and runbooks when code invalidates
  them;
- make uncertainty visible instead of inventing product behavior;
- run required project checks before review.

The pull request should explain the outcome, design decisions, compatibility
or migration effects, and evidence. Review compares implementation with the
linked design and specification. `ai-dlc work finish <work-id>` then verifies
the merged revision and remote evidence; it does not infer success from the
local branch.

## Change control

If implementation reveals a material product, interface, security, migration,
or operational decision that the design does not answer, pause and update the
reviewed artifact before continuing. Small implementation details may remain
in code and tests. Decisions that future maintainers must understand belong in
the repository.
