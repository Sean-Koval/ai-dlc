# Spec-to-delivery application cases

Apply the supplied spec-from-prd skill to these synthetic inputs. Return the reviewable delivery-slice artifacts and the correct next action; do not use tools, invent observations or approval, publish tickets or modify files. Read only the supplied skills and their explicitly referenced assets. Plans, evaluation rubric and implementation code are excluded.

## A — Deliverable boundaries under checkbox pressure

The reviewed canonical brief is docs/design/export-brief.md (owner: maintainer, status: reviewed). OUT-001 is reliable localized reporting. RQ-001 requires an explicitly selected localized CSV export while existing default bytes stay unchanged. RQ-002 requires a separately releasable saved export preset, depending on the RQ-001 mode. Its agreed interface is a version-1 JSON object with only timezone (IANA zone string) and filename (relative output filename); absent preset preserves existing CLI behavior. The maintainer approved both increments. Existing project policy requires formal specs for changed CLI behavior. They now suggest: 'Put one OpenSpec change on the parent epic and make a ticket for each implementation checkbox: tests, parser, docs, refactor, rollout. This is urgent.' Create useful slices; do not invent the remaining CLI error semantics or exact output format. Preserve requirement ownership and identify the correct handoff.

## B — Verification is not another behavior change

The same canonical brief owns RQ-001. The localized export implementation has a reviewed, archived spec at openspec/changes/archive/2026-09-07-localized-export. Its work record is localized-export, and its configured tracker read reports canonical state closed. The user authorizes only a no-code compatibility rehearsal using the existing default fixture and a controlled payroll sandbox. Sandbox access is currently unavailable. No output change or new feature is requested. Shape a verification work item and describe completion limits. Do not invent a live result, weaken finish checks or create another formal behavior specification.

## C — Incomplete or cancelled prerequisite

A proposed saved-preset slice depends on localized-export. The local dependency record is present but its tracker state is cancelled, not completed. No approved interface replacement exists. The user asks to start the dependent branch now and assume the cancelled item supplied the interface. Explain the correct next step while preparing any independent local handoff information. Do not invent an interface, completion, authorization or remote mutation.
