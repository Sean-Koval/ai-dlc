# Delivery slice: <work ID and outcome>

Owner: <decision owner or unknown>
Status: draft
Review source: <actual decision; do not invent approval>
Canonical brief: <document owning OUT-001/RQ-001; retain its IDs>

## Scope and exclusions

One independently finishable outcome, preserved contracts and excluded work.
A proposed local work ID is a draft identifier, not a published tracker ticket.

## Specification decision

requires_spec: <true for changed observable behavior; false for verification only>
spec_reason: <concrete reviewed reason>
Formal source: <this behavior ticket's own change, or existing behavior reference>

Keep formal behavior with the selected specification provider. An epic can group
work; it must not impose one shared specification completion gate on independent
children. OpenSpec tasks are implementation steps inside their behavior ticket.

## Traceability

| Canonical requirement | Formal scenario or no-new-spec reason | Deliverable work ID | Implementation step | Verification / evidence status |
| --- | --- | --- | --- | --- |
| <brief>#RQ-001 → OUT-001 | <exact scenario reference, or verification of existing behavior> | <local ID> | <step within this slice> | <observable check; planned/observed and source> |

Requirement labels are not parsed as paths. Include their source documents in
`artifacts` so local existence can be validated. Do not duplicate requirement
prose or make a new ticket for each test, parser, docs or refactoring checkbox.

## Dependencies and interfaces

| Dependency work ID | Required interface / source | Completion evidence or unavailable status |
| --- | --- | --- |
| <existing local work ID> | <approved contract; do not invent a replacement> | <fresh provider read, or not checked> |

An empty dependency list means none. A local graph check does not establish
completion. Start requires fresh canonical `closed`; cancelled/duplicate,
unpublished, incomplete or unavailable states block the dependent branch.

## Acceptance and implementation tasks

Describe observable success and preserved compatibility. Keep unapproved format
or error decisions in Open decisions rather than acceptance facts.

### Reviewed behavior check

Complete this mapping when the slice changes observable behavior or adopts a
behavior check. Cite exact repository sources and retain unknowns; filenames,
syntax checks and successful setup do not establish behavioral coverage.

| Requirement / check IDs | Observable behavior | Sources inspected | Exact command and command source | Prerequisites and reviewed setup action | Required or optional | Unknowns and review decision |
| --- | --- | --- | --- | --- | --- | --- |
| <RQ-001 / check-id> | <observable result> | <requirement, test config, CI, manifest paths> | <team-owned command and source> | <runtime/tool needs, setup action or unresolved> | <required/optional and why> | <accepted facts, unknowns, reviewer/source> |

Preserve authored tests, required IDs and unrelated commands. Apply configuration
only after the mapping and prerequisite choice are reviewed under the existing
authorization. Checks use the declared shell/runtime and install nothing. The
normal runner requires `mise` even with an empty tools table; an unavailable
runtime produces no passing evidence. Follow the canonical
[brownfield rehearsal](../workflows/brownfield.md#rehearse-a-reviewed-behavior-check)
in an external disposable fixture. A missed expected failure or failed isolation
is incomplete, and a focused passing result does not replace the full required run.

- [ ] Define acceptance/regression cases for this slice.
- [ ] Implement the scoped behavior, or execute the authorized verification.
- [ ] Update supporting documentation and collect actual evidence.
- [ ] Run required checks and review; satisfy configured finish gates.

## Work record draft

Fill only supported fields in `.ai-dlc/work/<id>.toml`; existing configured
providers/bindings are resolved through AI-DLC, not fabricated here. Put exclusions
in scope and detailed rationale/tasks in the linked delivery document.

```toml
schema = 1
id = "reviewed-slice"
title = "A bounded reviewed outcome"
scope = "State the outcome, compatibility boundaries and exclusions."
requires_spec = true
spec_reason = "State the reviewed behavior or verification decision."
requirements = ["brief#RQ-001"]
depends_on = []
acceptance = ["State an observable criterion with its verification."]
reviewed = false

[artifacts]
brief = "docs/design/brief.md"
spec = "openspec/changes/reviewed-slice"
plan = "docs/design/reviewed-slice.md"
```

These document destinations must exist before publication. Set reviewed only
from an actual review decision. For no-spec work, use `requires_spec=false` and
a concrete reason; reference the existing specification when useful. Provider
references (tracker/PR/branch/deployment/knowledge) are distinct from local paths.
HTTP(S) artifact references remain unprobed; local file/directory refs can include
fragments, whose specification meaning is reviewed by the appropriate provider.

## Open decisions and next action

List material unknowns, their owner and the smallest next action. Run
`ai-dlc work validate <id> --root .` before authorized publication. It is offline
and does not approve scope or qualify live services. Repeat publication reuses
an existing issue without overwriting authored descriptions. After implementation,
review and merge, use configured `ai-dlc work finish <id>` gates; a no-spec
verification item still needs applicable PR/CI evidence and real observations.

Decision: <proceed|investigate|stop> — <reason; no invented validation or approval>
