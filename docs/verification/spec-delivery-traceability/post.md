No tickets are published, no files are asserted to exist, and no validation was run. In Case A, the parent epic should coordinate two behavior slices; tests, parser, documentation, refactoring, and rollout remain tasks within those slices.

## A — Deliverable boundaries

### Slice A1: Localized export

**Identity and authority**

- Proposed local work ID: `localized-export` — draft only
- Owner: maintainer
- Review source: reviewed `docs/design/export-brief.md`
- Canonical references: `export-brief#RQ-001 → OUT-001`
- Delivery status: draft; the brief is reviewed, but the work record and specification are not

**Scope and exclusions**

Add an explicitly selected localized CSV export while preserving the existing default output byte-for-byte.

Excluded: saved presets, unrelated export features, unspecified output representation, unspecified CLI syntax, and unspecified error/exit behavior.

**Specification decision**

```text
requires_spec: true
spec_reason: Changes observable CLI behavior while preserving the default contract.
Formal source: openspec/changes/localized-export
```

This child needs its own OpenSpec change. A specification attached only to the parent epic would incorrectly couple independently finishable behavior.

**Traceability**

| Requirement | Formal scenario | Work ID | Implementation step | Evidence status |
| --- | --- | --- | --- | --- |
| `export-brief#RQ-001 → OUT-001` | Default invocation remains byte-compatible | `localized-export` | Characterize and preserve the default path | Planned; no observation supplied |
| `export-brief#RQ-001 → OUT-001` | Explicit selection produces localized CSV | `localized-export` | Add the reviewed CLI selection and localized-export behavior | Scenario incomplete pending exact output semantics |
| `export-brief#RQ-001 → OUT-001` | Invalid-input behavior | `localized-export` | Validate input before output | Not yet an executable scenario; error and exit semantics are undecided |

**Dependencies and interfaces**

`depends_on=[]`.

The existing default fixture and CLI are compatibility baselines, not completed predecessor work. Their actual contents were not inspected.

**Acceptance and tasks**

Approved acceptance boundary:

- Default invocation matches the existing fixture byte-for-byte.
- An explicit localization selection produces localized CSV according to this ticket’s subsequently reviewed formal scenarios.
- No acceptance claim is currently made about timestamp representation, selector syntax, invalid input, exit status, or partial output.

Tasks within this work item—not separate tickets:

- Resolve the exact localized output and CLI/error semantics with the maintainer.
- Author and review the formal scenarios.
- Add characterization and acceptance tests.
- Implement the CLI/parser and localized export behavior.
- Perform only supporting refactoring needed by this outcome.
- Update documentation and collect rollout/review evidence.
- Run required project checks and finish gates.

**Work record draft**

```toml
schema = 1
id = "localized-export"
title = "Add an explicitly selected localized CSV export"
scope = "Add the reviewed localized-export mode while preserving existing default bytes; exclude saved presets, unrelated export work, and semantics not yet approved."
requires_spec = true
spec_reason = "Changes observable CLI behavior while preserving the existing default contract."
requirements = ["export-brief#RQ-001"]
depends_on = []
acceptance = [
  "Without explicit localization selection, export bytes match the existing default fixture byte-for-byte.",
  "Explicit localization selection emits CSV according to the reviewed formal scenarios for this work item.",
]
reviewed = false

[artifacts]
brief = "docs/design/export-brief.md"
spec = "openspec/changes/localized-export"
plan = "docs/design/localized-export.md"
```

**Open decisions and next action**

The maintainer must decide the exact localized CSV representation, CLI selection syntax, and invalid-input/output/exit behavior. Until then, the affected scenarios are draft material, not executable acceptance criteria.

**Decision: investigate** — resolve those product semantics, then author and review this child’s formal change before implementation or publication.

---

### Slice A2: Saved export preset

**Identity and authority**

- Proposed local work ID: `saved-export-preset` — draft only
- Owner: maintainer
- Review source: reviewed `docs/design/export-brief.md`; both increments are approved
- Canonical references: `export-brief#RQ-002 → OUT-001`
- Delivery status: draft

**Scope and exclusions**

Add a separately releasable saved preset that invokes the RQ-001 localized-export mode. Its approved version-1 JSON shape contains only:

- `timezone`: an IANA zone string
- `filename`: a relative output filename

When no preset is supplied, existing CLI behavior remains unchanged.

Excluded: additional preset fields, absolute filenames, UI work, migrations, a general preset platform, and unspecified parsing/error behavior.

**Specification decision**

```text
requires_spec: true
spec_reason: Adds separately releasable preset-driven CLI behavior.
Formal source: openspec/changes/saved-export-preset
```

This behavior needs a separate OpenSpec change from `localized-export`.

**Traceability**

| Requirement | Formal scenario | Work ID | Implementation step | Evidence status |
| --- | --- | --- | --- | --- |
| `export-brief#RQ-002 → OUT-001` | No preset preserves existing CLI behavior | `saved-export-preset` | Preserve the no-preset path | Planned |
| `export-brief#RQ-002 → OUT-001` | A valid v1 object supplies the approved timezone and relative filename | `saved-export-preset` | Parse the two-field object and invoke the approved RQ-001 interface | Planned; dependent interface not yet evidenced |
| `export-brief#RQ-002 → OUT-001` | Invalid preset handling | `saved-export-preset` | Reject invalid input according to reviewed semantics | Not executable; semantics are undecided |

**Dependencies and interfaces**

| Dependency | Required interface | Status |
| --- | --- | --- |
| `localized-export` | Reviewed localized-export mode contract and its formal behavior | Completion status not supplied or freshly checked |

The approved preset shape does not establish that `localized-export` is complete. This branch cannot start until a fresh pinned-provider read reports canonical `closed`.

**Acceptance and tasks**

- A valid approved v1 object contains only `timezone` and `filename`.
- The filename is relative.
- A valid preset invokes the reviewed localized-export interface.
- Absence of a preset preserves existing CLI behavior.
- Malformed input, unknown fields, missing fields, and other failures remain open decisions.

Tasks within this work item:

- Confirm the predecessor’s reviewed interface and fresh canonical status.
- Resolve remaining preset CLI and error semantics.
- Author and review this ticket’s formal scenarios.
- Implement parsing and integration.
- Add acceptance and compatibility tests.
- Update documentation and collect required evidence.
- Run required checks and finish gates.

**Work record draft**

```toml
schema = 1
id = "saved-export-preset"
title = "Add a version-1 saved export preset"
scope = "Add the approved two-field JSON preset for the localized-export mode; preserve no-preset behavior and exclude additional fields, UI, migrations, and unapproved error semantics."
requires_spec = true
spec_reason = "Adds separately releasable preset-driven CLI behavior."
requirements = ["export-brief#RQ-002"]
depends_on = ["localized-export"]
acceptance = [
  "A valid version-1 preset contains only an IANA timezone string and a relative output filename.",
  "A valid preset invokes the reviewed localized-export interface.",
  "When no preset is supplied, existing CLI behavior remains unchanged.",
]
reviewed = false

[artifacts]
brief = "docs/design/export-brief.md"
spec = "openspec/changes/saved-export-preset"
plan = "docs/design/saved-export-preset.md"
```

**Open decisions and next action**

The maintainer owns the unresolved invocation and error semantics. The predecessor’s completion and interface must also be checked through its pinned provider.

**Decision: investigate** — prepare the local draft, but do not begin dependent implementation until semantics are reviewed and `localized-export` is freshly confirmed `closed`.

## B — No-code compatibility rehearsal

**Identity and authority**

- Proposed local work ID: `export-compatibility-rehearsal` — draft only
- Owner: maintainer
- Review source: supplied authorization for no-code verification
- Canonical references: `export-brief#RQ-001 → OUT-001`
- Existing behavior: `openspec/changes/archive/2026-09-07-localized-export`
- Supplied dependency observation: `localized-export` is canonically `closed`
- Sandbox status: unavailable

**Scope and exclusions**

Rehearse the existing default fixture in a controlled payroll sandbox and record the actual byte-level and consumer result.

Excluded: code changes, output changes, new features, contract changes, and another behavior specification.

**Specification decision**

```text
requires_spec: false
spec_reason: Verifies already specified default behavior without changing it.
Formal source: openspec/changes/archive/2026-09-07-localized-export
```

**Traceability**

| Requirement | Existing formal behavior | Work ID | Verification step | Evidence status |
| --- | --- | --- | --- | --- |
| `export-brief#RQ-001 → OUT-001` | Archived default byte-compatibility scenario | `export-compatibility-rehearsal` | Record fixture/revision/environment, execute the rehearsal, compare exact bytes, and record consumer outcome | Sandbox unavailable; no live result |

**Dependencies and interfaces**

| Dependency | Required source | Status |
| --- | --- | --- |
| `localized-export` | Reviewed default CSV contract and fixture | Supplied tracker state is `closed`; a fresh start-time read was not performed in this exercise |

**Acceptance and tasks**

- Record the fixture identity, revision, invocation, and controlled environment.
- Compare actual default output byte-for-byte.
- Record the actual payroll consumer result.
- Preserve unavailable access, mismatches, and failures as evidence.
- Do not treat a local fixture check as payroll-sandbox qualification.
- Apply all configured review, CI, evidence, and finish gates relevant to verification work.

**Work record draft**

```toml
schema = 1
id = "export-compatibility-rehearsal"
title = "Rehearse default export compatibility"
scope = "Verify existing default CSV compatibility in a controlled payroll sandbox; exclude code, format, contract, and feature changes."
requires_spec = false
spec_reason = "Verifies already specified default behavior without changing it."
requirements = ["export-brief#RQ-001"]
depends_on = ["localized-export"]
acceptance = [
  "Record fixture identity, revision, invocation and controlled environment.",
  "Observe and compare the exact default bytes.",
  "Record the actual sandbox consumer result, including unavailability or mismatches.",
]
reviewed = false

[artifacts]
brief = "docs/design/export-brief.md"
spec = "openspec/changes/archive/2026-09-07-localized-export"
plan = "docs/runbooks/export-compatibility-rehearsal.md"
```

**Completion limits and next action**

The work cannot finish while sandbox access is unavailable. No live compatibility result exists, and fixture-only checks cannot replace it. Before an actual start, the dependency must again be read through its pinned provider.

**Decision: investigate** — prepare and review the bounded runbook, obtain authorized sandbox access, refresh the dependency status, and then record real observations.

## C — Cancelled prerequisite

**Identity and authority**

- Proposed local work ID: `saved-export-preset` — draft only
- Owner: maintainer
- Canonical reference: `export-brief#RQ-002 → OUT-001`
- Dependency: `localized-export`
- Observed tracker state: `cancelled`
- Approved replacement interface: none

**Scope and specification**

The saved-preset slice may be documented locally, but it remains dependent on an approved, completed localized-export interface.

```text
requires_spec: true
spec_reason: The preset would add observable CLI behavior.
Formal source: openspec/changes/saved-export-preset
```

Its formal scenarios cannot be completed by assuming behavior from the cancelled item.

**Dependency record**

| Dependency | Required interface | Completion evidence |
| --- | --- | --- |
| `localized-export` | Approved localized-export mode consumed by the preset | Canonical state `cancelled`; start is blocked |

`cancelled` does not satisfy the required canonical `closed` state. A present local record or valid local dependency graph does not change that result.

**Independent local handoff**

The following draft can preserve requirement ownership and the known dependency without claiming it is startable:

```toml
schema = 1
id = "saved-export-preset"
title = "Add a saved export preset"
scope = "Add the reviewed saved-preset outcome only after an approved localized-export interface is available; preserve no-preset behavior and exclude invented replacement behavior."
requires_spec = true
spec_reason = "Would add observable preset-driven CLI behavior."
requirements = ["export-brief#RQ-002"]
depends_on = ["localized-export"]
acceptance = [
  "When no preset is supplied, existing CLI behavior remains unchanged.",
  "Preset integration uses an owner-approved and completed localized-export interface.",
]
reviewed = false

[artifacts]
brief = "docs/design/export-brief.md"
spec = "openspec/changes/saved-export-preset"
plan = "docs/design/saved-export-preset.md"
```

The second acceptance entry is a prerequisite boundary, not evidence that an interface currently exists. Dependent executable scenarios remain pending.

**Open decisions and next action**

The maintainer must decide whether to restore and complete `localized-export` or approve a replacement work item and interface. The dependency link and formal preset scenarios can then be updated through review. Starting now, creating an assumed interface, or treating cancellation as completion would violate the dependency contract.

**Decision: stop** — do not start the dependent branch. Preserve the local draft, resolve the predecessor or approve a replacement, and require a fresh canonical `closed` read before starting.
