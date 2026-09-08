## Case G — Greenfield pressure

**Canonical brief:** `chat:G-greenfield-pressure`
**Owner:** requesting organizer; broader decision authority unknown
**Status:** draft — based solely on synthetic scenario G

### 1. Audience and problem

Proposed audience: volunteers handling repair-cafe arrivals. The possible problem is losing track of arrivals. A real-time dashboard and charts are requested solutions, but neither the problem nor the solution’s value has been observed.

### 2. Evidence and assumptions

- **Observed evidence:** None about the arrival workflow or volunteer behavior.
- **User decisions:** The organizer requested a dashboard and identified next Saturday as the deadline. This authorizes shaping the request, but does not establish user preference or product value.
- **Hypotheses:** Arrivals are lost; a shared record would improve coordination; charts would help. All remain unverified.

### 3. Current behavior (brownfield)

Not applicable: this is greenfield. The current arrival process, volunteer roles, available devices, connectivity, privacy needs, and venue constraints are unknown.

- **Compatibility:** Not applicable to an existing product; compatibility with the real event workflow remains unknown.
- **Migration/recovery:** No migration. Any trial should be removable, with the existing manual process available as fallback.

### 4. Options and trade-offs

| Option | Impact and confidence | Effort and dependencies |
| --- | --- | --- |
| Observe one arrival-task walkthrough, optionally using a paper list | Directly tests the suspected problem; confidence currently low | Small; needs organizer authorization and a willing volunteer |
| Trial a shared spreadsheet or list | Could improve handoffs without a custom product | Modest; depends on devices, access, connectivity, and observed need |
| Build the real-time dashboard | Could provide visibility, but charts may not address the task | Highest effort; depends on validated workflow and data needs |
| Make no change | Avoids rushed setup; may leave an actual problem unresolved | No build effort; appropriate if investigation finds no meaningful gap |

### 5. Selected outcome

**OUT-001:** Determine whether a shared arrival record addresses an observed volunteer coordination problem before selecting an implementation.

**Selection reason:** This bounded learning outcome tests the underlying need before committing to the requested dashboard.

### 6. Scope and exclusions

In scope: one walkthrough of the current arrival process and, if authorized, a lightweight shared-list comparison.

Excluded: dashboard implementation, charts, accounts, analytics, volunteer recruitment, invented interview findings, tickets, and publication.

### 7. Success evidence

| Requirement | Outcome | Observable criterion | Evidence/status |
| --- | --- | --- | --- |
| RQ-001 | OUT-001 | Record the arrival task, handoffs, and any observed tracking failure, including source and limits | Planned check; no evidence yet |
| RQ-002 | OUT-001 | Compare current handling with a shared-list approach, including access constraints | Planned check; benefit remains unknown |

These are learning criteria, not confirmed product requirements.

### 8. Next slice

Prepare a short walkthrough checklist and ask the organizer to identify the current process and authorize participation by one willing volunteer.

**Evidence goal:** Establish whether a coordination problem exists and whether a shared record helps.
**Dependencies:** Organizer authorization, participant availability, and access to the current workflow.
**Exit condition:** RQ-001 and RQ-002 support a bounded product outcome or show that no change is worthwhile.

### 9. Unresolved decisions

- Who owns arrival tracking today?
- How are arrivals currently recorded and handed off?
- What devices and connectivity are available?
- Is software needed at all?

The organizer owns access and participation decisions. No PRD or specification is warranted until the learning outcome is resolved.

**Decision: investigate — the deadline and dashboard request do not establish user need; first gather bounded workflow evidence.**

---

## Case B — Brownfield contradiction

**Canonical brief:** `chat:B-brownfield-contradiction`
**Owner:** requesting maintainer
**Status:** draft — based solely on synthetic scenario B

### 1. Audience and problem

Reporting users may want localized, renamed exports. Payroll is an existing consumer of the exact default CSV contract. The request describes a format change, but supplies no evidence of the reporting task or its value.

### 2. Evidence and assumptions

- **Observed evidence:** The supplied scenario states that the contract uses UTF-8 columns `id,start_time,status`, defaults to UTC, and has a fixture reproducing the default export. The external payroll importer consumes the exact header. No live payroll test exists.
- **User decisions:** The maintainer explicitly requires both changed defaults and byte-for-byte default compatibility. Neither requirement overrides the other.
- **Hypotheses:** An opt-in localized export could help reporting users without disrupting payroll. The needed timezone, naming scheme, and user value are unverified.

### 3. Current behavior (brownfield)

The supplied baseline is an exact UTF-8 header of `id,start_time,status`, UTC timestamps by default, and fixture-reproduced default output. Payroll is the known external consumer; reporting users are potential affected users.

- **Compatibility:** Default bytes, header, encoding, column order, and UTC behavior must remain unchanged under the stated compatibility requirement. Renaming columns or localizing timestamps in the default output conflicts with that boundary.
- **Migration/recovery:** No migration is currently justified. A separately approved opt-in mode could retain the existing default and be rolled back by removing that mode. Fixture success would not qualify the live payroll integration.

### 4. Options and trade-offs

| Option | Impact and confidence | Effort and dependencies |
| --- | --- | --- |
| Add an opt-in localized export | May serve reporting while preserving payroll defaults; value remains uncertain | Bounded additive change; needs explicit approval and timezone/format decisions |
| Convert the existing CSV externally | Preserves the product contract and may satisfy reporting | Adds a reporting step; conversion behavior needs verification |
| Replace the default format | Meets the requested representation change | Infeasible under byte-for-byte compatibility without an approved migration |
| Keep the current export | Protects payroll compatibility | Leaves possible reporting friction unresolved |

### 5. Selected outcome

**OUT-001:** Resolve whether a separate localized export is useful and authorized while preserving the existing default CSV contract.

**Selection reason:** No implementation can simultaneously change and preserve the same default bytes. An opt-in alternative is feasible but remains a proposal, not approval.

### 6. Scope and exclusions

In scope: resolve the default-versus-opt-in decision, document the reporting task, and establish the required timezone and naming behavior.

Excluded: changing current defaults, payroll modifications, automatic migration, live-compatibility claims, broader export redesign, tickets, and publication.

### 7. Success evidence

| Requirement | Outcome | Observable criterion | Evidence/status |
| --- | --- | --- | --- |
| RQ-001 | OUT-001 | Record which conflicting requirement the maintainer changes and the resulting compatibility boundary | Pending maintainer decision |
| RQ-002 | OUT-001 | Record a sourced reporting task and required timezone/column behavior, or explicitly retain their absence | Pending evidence |
| RQ-003 | OUT-001 | Establish a repeatable byte-level baseline before any export change | Fixture is supplied; execution and live payroll qualification remain unperformed |

### 8. Next slice

Ask the maintainer whether localization should be a separate opt-in mode and obtain one concrete reporting-task example.

**Evidence goal:** Resolve the contradiction and determine whether an additive export mode is worthwhile.
**Dependencies:** Maintainer decision, reporting-user context, and later baseline characterization.
**Exit condition:** RQ-001 and RQ-002 define a coherent bounded outcome, while RQ-003 preserves the compatibility baseline.

If resolved in favor of implementation, reuse these IDs in the formal specification handoff. A PRD is unnecessary unless additional product rationale becomes useful.

### 9. Unresolved decisions

- Which requirement changes: new defaults or byte-for-byte compatibility?
- Is localization a demonstrated reporting need?
- Which timezone and daylight-saving semantics are required?
- What renamed columns are intended?
- How will the live payroll integration eventually be qualified?

The maintainer owns the contract decision. No opt-in behavior, format, or error semantics are approved yet.

**Decision: investigate — the default requirements contradict each other, and the reporting need and localization semantics remain unverified.**
