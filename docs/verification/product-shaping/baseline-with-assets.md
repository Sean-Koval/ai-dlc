## G — Greenfield pressure

**Classification:** Discovery required; implementation is premature.

- **Problem:** Volunteers may lose track of arrivals during repair-cafe operations.
- **Requested outcome:** Better coordination for next Saturday.
- **Suggested implementation:** A beautiful real-time dashboard with charts. This is unvalidated and should not be treated as the requirement.
- **Known evidence:** None from interviews, observation, an existing product, or operational data.
- **Assumptions:** Arrival tracking is a real problem; volunteers would use a shared digital display; charts would improve decisions.
- **Open questions:** Who tracks arrivals now? Where does the process fail? What decisions need support? What devices and connectivity are available? Would a paper queue or shared list suffice?
- **Smallest useful investigation:** Observe or rehearse one arrival-to-assignment workflow with the organizer and two volunteers. Record roles, failure points, essential fields, and the minimum shared view needed.

**Next-action decision:** Do not start dashboard implementation. Run the bounded workflow investigation, then choose the smallest intervention supported by evidence.

## B — Brownfield contradiction

**Classification:** Blocked discovery/decision; not ready for requirements or implementation.

- **Problem:** The maintainer wants localized timestamps and renamed columns, but the existing default export is a checked-in, externally consumed contract.
- **Known evidence:** The default is UTF-8 with `id,start_time,status` and UTC timestamps; an external payroll importer consumes that header; a fixture reproduces the default bytes.
- **Contradiction:** Changing default headers or timestamp bytes cannot coexist with byte-for-byte default compatibility.
- **Risk:** A default change could silently break payroll. The fixture provides repository-level characterization, not live importer verification.
- **Assumptions:** An opt-in or versioned format might satisfy the new need without altering the default, but neither is authorized.
- **Open question:** Which requirement yields: new defaults, exact compatibility, or the absence of a separate export mode?
- **Smallest useful investigation:** Present the contradiction and compatibility-preserving alternatives to the maintainer for an explicit decision. Use the fixture as the current-contract baseline; do not claim live payroll compatibility.

**Next-action decision:** Stop before drafting or coding. Obtain a recorded product decision, preferably whether to pursue a separate opt-in/versioned export while preserving the existing default.

## P — Bounded, reviewed non-UI work

**Product requirements**

Owner: Maintainer
Status: draft

### Problem and audience

The reporting team performs manual timezone conversions when using scheduling exports. The maintainer has reviewed and authorized a separate, opt-in localized export mode.

### Outcomes and acceptance

- Reporting-team users can deliberately request a localized export.
- The existing default export remains byte-for-byte identical to the characterized fixture.
- The localized mode produces the agreed localized timestamp representation.
- Both modes are covered by repeatable repository tests.
- No numerical business-impact baseline is asserted; the supplied support log establishes the qualitative problem only.

### Scope and exclusions

**In scope:** One opt-in localized CSV export mode and its tests/documentation.

**Excluded:** Changes to default export bytes, payroll importer changes, schema migration, UI, and new services.

### Constraints and risks

- Default compatibility is mandatory.
- Localization must define timezone selection and handling of daylight-saving transitions.
- Renamed columns should not be assumed unless separately approved for the opt-in mode.
- Repository tests cannot establish live payroll behavior.

### Open questions

- Which timezone and timestamp representation should the opt-in mode use?
- Does the localized mode retain the existing header or use a separately approved header?
- How does a caller select the mode?
- What should happen for ambiguous or nonexistent local times?

### Links

Evidence: characterized default fixture and maintainer-supplied support log.
Future formal behavior belongs in the specification role; tracker linkage can follow authorization.

**Next-action decision:** The increment is approved and bounded, but coding should begin only after the remaining format and timezone choices are confirmed and expressed as acceptance examples. Then implement the opt-in path with a regression test proving unchanged default bytes.

## S — Explicit stop

**Classification:** Duplicate; declined; no action.

- **Duplicate:** An existing tracked feature already covers the request.
- **Priority/audience fit:** The maintainer explicitly states it does not serve the current audience.
- **Missing context:** None needed for triage; the decision is explicit.
- **Durable handling:** Keep the existing tracker history unchanged. Do not convert personal notes into new durable work.

**Next-action decision:** Close the inbox item as “duplicate—declined.” Do not create, reopen, republish, or externally reply about the feature.
