Based only on the supplied skill and scenario text, with no external actions taken:

## A — Deliverable boundaries

### Traceability and ownership

- Canonical PRD: `docs/design/export-brief.md`
- Status: reviewed
- Owner: maintainer
- Outcome: OUT-001
- Requirements: RQ-001 and RQ-002
- Ownership remains with the canonical brief. Specifications and work records refine and implement these requirements; they do not become replacement requirement sources.

### Proposed delivery slices

| Slice | Behavior delivered | Dependency | Formal specification |
|---|---|---|---|
| A1 — Localized CSV mode | RQ-001: explicitly selected localized export while default bytes remain unchanged | None stated | Its own OpenSpec change |
| A2 — Saved export preset | RQ-002: optional version-1 preset containing only `timezone` and `filename` | Completed A1 interface | Separate OpenSpec change |

Each change must link to the canonical brief, its owned requirement, and its own provider-created work record. No work-record identifiers should be invented here.

The parent epic can coordinate both slices, but one epic-level OpenSpec change would obscure RQ-002’s separate release boundary and dependency.

### A1 draft requirements and scenarios

Requirements:

- The existing default invocation must continue producing exactly the existing bytes.
- Localized CSV behavior must occur only when explicitly selected.
- The localized representation and CLI contract must follow product-approved rules that are not yet supplied.

Scenarios:

```gherkin
Scenario: Existing default remains byte-compatible
  Given the same input and configuration used by the existing default fixture
  And localized export is not selected
  When the export runs
  Then its bytes equal the existing default fixture
```

```gherkin
Scenario: Explicitly select localized export
  Given the user explicitly selects localized CSV mode
  When the export runs
  Then it uses the product-approved localized CSV representation
```

The second scenario is not yet executable because the exact representation and selection syntax are unresolved.

### A2 draft requirements and scenarios

Requirements:

- The preset is a version-1 JSON object containing only:
  - `timezone`: an IANA timezone string
  - `filename`: a relative output filename
- The preset depends on the RQ-001 localized-export mode.
- When no preset is supplied, existing CLI behavior remains unchanged.
- Invalid-input behavior must not be inferred.

Scenarios:

```gherkin
Scenario: No preset preserves existing behavior
  Given no saved export preset is supplied
  When the CLI runs
  Then its existing behavior is unchanged
```

```gherkin
Scenario: Use a valid saved preset
  Given the localized-export capability is available
  And a selected preset contains a valid IANA timezone
  And its filename is relative
  When the localized export runs
  Then it applies that timezone and output filename
```

```gherkin
Scenario: Preset contains unsupported or invalid data
  Given a preset has an additional property, invalid timezone, or non-relative filename
  When the preset is processed
  Then the result follows the product-approved error behavior
```

The final scenario deliberately leaves the outcome unresolved.

### Checkbox disposition

`tests`, `parser`, `docs`, `refactor`, and `rollout` are not five delivery slices merely because they are checkboxes.

- Parser, tests, and documentation belong under the behavior slice they support.
- Refactoring is an internal task unless it independently delivers an approved outcome.
- Rollout belongs in release or operational checks; it becomes a separate work item only if it has an independently reviewable operational outcome.
- None should acquire ownership of RQ-001 or RQ-002.

### Decision and handoff

**Decision: stop before creating or validating the formal specifications.**

The maintainer must resolve at least:

- The localized CSV representation.
- The precise CLI selection mechanism.
- How a preset is selected and how it interacts with explicit mode selection.
- Error behavior for malformed CLI input, unreadable or malformed presets, invalid timezones, non-relative filenames, and unsupported fields.

After those decisions are approved in the canonical brief or an authoritative linked decision record, hand A1 and A2 separately to the configured specification role. The provider should then store, validate, and link each OpenSpec change and work record.

---

## B — Verification is not a behavior change

### Verification work item

**Type:** compatibility rehearsal, not a behavior specification
**Traceability:**

- Requirement: RQ-001
- Existing specification: `openspec/changes/archive/2026-09-07-localized-export`
- Work record: `localized-export`
- Canonical tracker state: closed

**Authorized scope:**

- No code changes.
- Use the existing default fixture.
- Rehearse in the controlled payroll sandbox.
- Verify that the default path remains byte-compatible.
- Record the environment, invocation, fixture identity, and observed comparison when execution becomes possible.

Proposed finish checks:

```text
[ ] Controlled payroll sandbox access is available and authorized.
[ ] The approved existing default fixture is identified without modification.
[ ] The rehearsal is executed in the controlled sandbox.
[ ] Actual output is compared byte-for-byte with the fixture.
[ ] The invocation, environment, artifacts, and observed result are recorded.
[ ] Any mismatch is reported for triage without making an unauthorized fix.
```

### Completion limits

Sandbox access is unavailable, so:

- No rehearsal result exists.
- The work item cannot be marked passed or complete.
- A fixture review outside the sandbox would be preparatory evidence only; it would not satisfy the authorized finish checks.
- A mismatch would trigger evidence-backed triage against the existing requirement/specification. It would not automatically justify a new behavior specification or code change.

### Next action

**Status: blocked.** Obtain authorized access to the controlled payroll sandbox, then execute the existing-spec compatibility rehearsal. Do not create another OpenSpec change.

---

## C — Cancelled prerequisite

### Blocked handoff artifact

```text
Dependent slice: saved preset
Required prerequisite: localized-export
Local dependency record: present
Canonical tracker state of prerequisite: cancelled
Approved replacement interface: none
Dependent branch authorization: not established
Disposition: blocked
```

Independent handoff facts:

- The saved-preset proposal depends on localized-export.
- The canonical state does not establish that the prerequisite was delivered.
- A cancelled work item cannot be treated as a completed interface contract.
- There is no approved replacement interface to specify or implement against.
- No branch, formal specification, remote work record, or implementation should be started from the unsupported assumption.

### Next action

**Do not start the dependent branch.** Return the dependency conflict to the requirement owner or maintainer for one of these explicit decisions:

1. Revive and approve completion of localized-export.
2. Approve a replacement prerequisite and interface, then update the dependency.
3. Rescope, defer, or cancel the saved-preset slice.

Only after an approved prerequisite/interface exists should the configured specification role formalize the dependent behavior and hand it to delivery.
