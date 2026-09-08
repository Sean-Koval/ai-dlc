## G — Greenfield pressure

### Audience and problem

Proposed audience: repair-cafe arrival volunteers. The possible problem is losing track of arrivals; the requested real-time dashboard and charts are unvalidated solutions.

### Evidence and assumptions

- Observed evidence: none; no product, interview, or task observation exists.
- User decisions: the organizer requests a dashboard by next Saturday and asks to begin implementation. This authorizes neither participant contact nor proof that charts are valuable.
- Hypotheses: volunteers lose arrivals and might benefit from a shared record.

### Current behavior (brownfield)

Not applicable. The current arrival process, volunteer roles, devices, access, and venue connectivity are unknown external constraints.

### Options and trade-offs

- Observe one arrival-task walkthrough: lowest effort and best learning value; requires an authorized, willing participant.
- Trial a paper list or shared spreadsheet: may reveal whether a shared record helps, but access and connectivity remain unknown.
- Build the dashboard: highest effort with little evidence that real-time charts address the task.
- Do nothing: avoids rushed work and remains appropriate if no coordination problem is demonstrated.

### Selected outcome

OUT-001: Determine whether a shared arrival record addresses an observed volunteer coordination problem before selecting an implementation.

Reason: the smallest worthwhile increment is learning whether the problem exists, not committing to the requested presentation.

### Scope and exclusions

One walkthrough of the current arrival process and, if authorized, a lightweight shared-list comparison. Exclude dashboard implementation, charts, accounts, analytics, volunteer recruitment, and publication.

### Success evidence

| Requirement | Outcome | Observable criterion | Status |
| --- | --- | --- | --- |
| RQ-001 | OUT-001 | Record the current task, handoffs, and any observed tracking failure with source and limits | Planned; no observations yet |
| RQ-002 | OUT-001 | Compare current handling with a shared-record trial, including device and access constraints | Planned; benefit remains unknown |

### Next slice

Ask the organizer to identify the current process and authorize participation by one willing volunteer. Exit when the walkthrough either supports a bounded shared-record outcome or finds no worthwhile problem.

### Unresolved decisions

Who owns arrivals, how they are recorded, whether volunteers can share a device, and whether software is necessary. The organizer owns access and participation decisions.

Decision: investigate — the deadline and dashboard request do not establish user value; gather bounded task evidence before implementation.

---

## B — Brownfield contradiction

### Audience and problem

Reporting staff may need localized exports, while payroll depends on the existing CSV. The requested format change is distinct from the underlying, presently unverified reporting need.

### Evidence and assumptions

- Observed evidence: the supplied contract and fixture establish UTF-8 columns `id,start_time,status`, UTC defaults, and reproducible default output. A payroll importer consumes the exact header.
- User decisions: both changing the defaults and preserving default bytes are explicit requirements; neither overrides the other.
- Hypotheses: an opt-in localized mode might help reporting staff without disrupting payroll. Its value and timezone semantics are unverified.

### Current behavior (brownfield)

The default export uses UTF-8, the exact header `id,start_time,status`, and UTC timestamps. Byte compatibility is a stated boundary. The fixture characterizes that behavior but does not qualify the live payroll integration. No migration requirement is established.

### Options and trade-offs

- Separate opt-in localized export: preserves defaults, but requires approval plus timezone and format decisions.
- External conversion: avoids changing the product contract but adds a reporting step and needs validation.
- Replace the default format: conflicts with explicit byte compatibility and is infeasible without an approved migration.
- Keep current behavior: protects payroll but may leave reporting friction.

### Selected outcome

OUT-001: Resolve whether a separate localized export is useful and authorized while preserving the existing default contract.

Reason: no implementation can meet both contradictory default requirements.

### Scope and exclusions

Clarify the default-versus-opt-in decision and reporting need. Preserve existing default bytes, header, encoding, and UTC behavior. Exclude payroll changes, migration, UI, and publication.

### Success evidence

| Requirement | Outcome | Observable criterion | Status |
| --- | --- | --- | --- |
| RQ-001 | OUT-001 | Record the maintainer’s resolution of the contradictory default requirements | Pending decision |
| RQ-002 | OUT-001 | Establish the reporting task and required timezone behavior, or explicitly retain their absence | Pending evidence |
| RQ-003 | OUT-001 | Preserve a repeatable exact-byte baseline for the default export | Fixture supplied; live payroll unverified |

### Next slice

Ask the maintainer whether localization may be a separate opt-in mode and obtain a concrete reporting example. Exit when the compatibility boundary and reporting requirement are resolved.

### Unresolved decisions

Which conflicting requirement changes; whether localization is genuinely needed; target timezone, daylight-saving behavior, columns, and format semantics. The maintainer owns these decisions.

Decision: investigate — the default requirements contradict each other, and an opt-in alternative has not been approved.

---

## P — Bounded, reviewed non-UI work

### Audience and problem

The reporting team performs manual timezone conversions when using scheduling exports. The approved solution boundary is a separate opt-in localized CSV mode, not a change to the existing default export.

### Evidence and assumptions

- Observed evidence: repository characterization confirms the current default contract; the maintainer-supplied support log records manual conversions. The log demonstrates reported workflow friction, not its frequency or numerical business impact.
- User decisions: the maintainer reviewed and authorized only the opt-in mode. Existing default bytes must remain unchanged; payroll changes, migration, UI, and new services are excluded.
- Hypotheses: the opt-in mode will reduce manual conversion work. Live value and integration behavior remain unverified.

### Current behavior (brownfield)

The existing default CSV contract remains the compatibility baseline. Payroll consumes it and must see no byte-level change. No localized product mode currently exists. Repository characterization is not live payroll qualification.

### Options and trade-offs

- Authorized opt-in mode: directly addresses recorded manual conversion while isolating compatibility risk; requires formal timezone and output semantics.
- Document an external conversion workflow: smaller implementation impact but preserves manual work and falls outside the approved product outcome.
- Change the default: explicitly excluded and incompatible.
- Do nothing: preserves compatibility but leaves evidenced reporting friction.

### Selected outcome

OUT-001: Provide an explicitly selected localized CSV export mode for the reporting team while preserving the existing default export byte-for-byte.

Reason: the audience, problem evidence, compatibility boundary, and solution scope have been reviewed and authorized.

### Scope and exclusions

Include only the opt-in export mode and verification of unchanged default bytes. Exclude default changes, payroll modifications, schema migration, UI, new services, and claims of live success.

### Success evidence

| Requirement | Outcome | Observable criterion | Status |
| --- | --- | --- | --- |
| RQ-001 | OUT-001 | An explicitly selected mode produces localized timestamps according to formally specified timezone and CSV semantics | Proposed criterion; semantics require specification |
| RQ-002 | OUT-001 | Without opt-in selection, the characterized default output remains byte-for-byte unchanged | Confirmed compatibility requirement; regression check required |
| RQ-003 | OUT-001 | Representative conversion cases, including applicable offset transitions, satisfy the formal specification | Planned verification; cases and expected results not yet specified |

### Next slice

Hand OUT-001 and RQ-001–RQ-003 to needs-spec and the configured formal specification provider. Define selection, timezone source, daylight-saving behavior, columns, encoding, and error behavior without changing the approved scope. Exit when those semantics are reviewable and default-compatibility checks are identified.

A separate PRD is unnecessary unless stakeholders need more durable rationale; this brief is sufficient as the canonical product authority.

### Unresolved decisions

The formal specification must resolve timezone selection, ambiguous or nonexistent local times, exact localized representation, and error behavior. These are not silently approved by the opt-in authorization. Live payroll and user-value verification remain unperformed.

Decision: proceed — evidence and authorization support the bounded outcome; proceed to formal specification, not implementation, while preserving default bytes.

---

## S — Explicit stop

- **Item/source:** Incoming request for a feature already represented by existing tracked work; maintainer response explicitly declines it.
- **Classification:** Duplicate and declined; does not serve the current audience.
- **Evidence and user decisions:** The supplied scenario states that related tracked work exists and that the maintainer explicitly declined the request. No tracker identifier was supplied.
- **Hypotheses/missing context:** None needs resolution for triage. Further product discovery would improperly reopen a settled decision.
- **Duplicate or related work:** Existing tracked feature; reference it only if its known identifier is later supplied.
- **Priority rationale:** No current-audience benefit is claimed, and the authoritative maintainer decision is to decline it. Additional shaping or publication would create duplicate work.
- **Next action and decision:** Preserve the decline reason in the current review context. Do not create a brief or PRD, reopen the tracked feature, republish the request, or send an external reply.

Decision: stop — the request is both duplicate and explicitly declined.