## G — Greenfield pressure

**Applied skill:** Discovery

- **Requested outcome:** Volunteers reliably track repair-cafe arrivals next Saturday.
- **Suggested implementation:** A beautiful real-time dashboard with charts. This is unvalidated and should not yet define the solution.
- **Known evidence:** None from interviews, observation, an existing product, or workflow data.
- **Assumptions:** Arrivals are currently lost; volunteers need real-time visibility; charts would help; a new product can be safely introduced before the event.
- **Bounded problem statement:** We do not yet know whether volunteers lose track of arrivals, where breakdowns occur, or what minimum intervention would improve the event.
- **Open questions:** Who handles arrivals? What information must be captured? What currently fails? How many people coordinate? What devices and connectivity are available? What does “tracked” mean operationally?
- **Smallest useful investigation:** Observe or walk through one representative arrival workflow with the event organizer and one volunteer. Identify the failure point and test a lightweight process prototype, such as a shared check-in list.

**Final next action:** Do not start dashboard implementation. Run the focused workflow investigation and then decide whether any software increment is justified.

## B — Brownfield contradiction

**Applied skills:** Discovery and Review Inbox

- **Classification:** Valid compatibility-sensitive request, but blocked by contradictory requirements.
- **Existing evidence:** The checked-in contract and fixture establish the default UTF-8 header and UTC behavior. An external payroll importer depends on that exact header. There is no live payroll verification.
- **Contradiction:** Localized timestamps and renamed default columns cannot coexist with byte-for-byte default compatibility.
- **Assumption:** An opt-in export mode or versioned format may satisfy both underlying needs, but neither has been authorized.
- **Risks:** Breaking payroll ingestion; silently changing timezone semantics; treating fixture coverage as live integration verification.
- **Missing decision:** Which requirement governs the default behavior, or whether the localized format must be separate and opt-in.
- **Smallest useful investigation:** Present the incompatibility to the maintainer with two explicit choices: preserve the default and add an opt-in format, or intentionally introduce a breaking default with a coordinated payroll migration.

**Final next action:** Block implementation pending the maintainer’s compatibility decision. Recommend preserving the existing default and separately authorizing an opt-in mode, without treating that recommendation as approval.

## P — Bounded, reviewed non-UI work

**Applied skill:** PRD Draft

**Status:** Draft increment brief; implementation is authorized, but requirements should be confirmed before coding.

- **Audience:** Reporting team.
- **Problem:** The reporting team manually converts default UTC timestamps for localized reporting.
- **Outcome:** Provide an opt-in localized CSV export while retaining the existing default export byte-for-byte.
- **Evidence:** Repository characterization confirms the default contract; the maintainer-supplied support log documents manual timezone conversion. No numerical business baseline is established.
- **Acceptance criteria:**
  - Exporting without the new option produces bytes identical to the existing fixture.
  - The opt-in mode emits the approved localized timestamps and column names.
  - The selected timezone is explicit and deterministic.
  - Invalid or missing localization inputs produce defined errors or documented fallback behavior.
  - Tests cover default compatibility, representative localized output, and timestamp edge cases such as daylight-saving transitions.
- **Scope:** Only the separate opt-in CSV mode and its automated tests/documentation.
- **Out of scope:** Payroll importer changes, default-format changes, schema migration, UI, and new services.
- **Constraints:** Preserve the checked-in default contract; do not claim live payroll verification.
- **Risks:** Ambiguous timezone selection, daylight-saving behavior, renamed-column collisions, and accidental leakage of localized behavior into the default path.
- **Open questions:** Exact opt-in interface, approved localized headers, timestamp format, timezone source, and daylight-saving ambiguity policy.

**Final next action:** Resolve the remaining format/interface questions, encode them as acceptance tests, and then implement the isolated opt-in mode while retaining the existing fixture as the default-compatibility guard.

## S — Explicit stop

**Applied skill:** Review Inbox

- **Classification:** Duplicate, declined, and outside the current audience’s needs.
- **Duplicate:** The feature already exists as tracked work.
- **Decision evidence:** The maintainer explicitly declined it.
- **Missing context:** None needed for triage.
- **Durable action:** No new ticket, design document, external reply, reopening, or republication.

**Final next action:** Close the inbox item as a declined duplicate and take no further action.