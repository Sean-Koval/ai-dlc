# Plane new-work verification

This bounded child of [issue 20](https://github.com/Sean-Koval/ai-dlc/issues/20)
implements optional Plane configuration and lifecycle for future new work. See
[design and official sources](../design/plane-new-work.md) and the
[setup/recovery runbook](../runbooks/plane-setup.md). No Plane installation,
deployment, account login or service mutation occurred.

The checkout starts from Jira e377d720 and includes its independent-review repair
03d5cbe as equivalent local commit 03f8c37. Jira's separate review checkout is not
changed by this Plane work. Shared bootstrap was not retried because the
coordinator identified concurrent executable publication problems. This child
used the existing stable user uv and interpreter to prepare its own editable
virtual environment. The initial targeted run used Python 3.14; a required-check run was stopped when it exposed the project's 3.12 selection. Only that owned process tree was stopped; the environment was rebuilt explicitly with the already installed Python 3.12.11 before final required validation. Commands select this checkout's `.venv/bin` explicitly;
this is local prepared-environment evidence, not a fresh bootstrap qualification.

## Behavior and evidence scope

The 61 new Plane cases exercise real provider behavior with `httpx.MockTransport`,
real local files, six competing processes for the immutable-intent boundary, and
real WorkService/Registry/Journal flow. SCM merged-PR and CI evidence in lifecycle
tests is explicitly synthetic. Central bundled registration is separately tested
through the actual executable capability boundary with trusted root/state
arguments; provider wire results are checked against the shared contract.

| Requirement | Evidence |
| --- | --- |
| PN-01 | API-key and externally managed Bearer headers, strict Cloud/self-hosted origins, localhost/IPv4/IPv6 loopback HTTP, bad ports/authority/redirect/account/foreign-reference refusal, no credential-bearing response diagnostics. |
| PN-02 | Same-create escaped visible marker and scoped external pair; full multi-page find; inconsistent counts/cursors, duplicate UUIDs/correlations, damaged marker, required response shape and resource identity refusal. |
| PN-03 | Durable exclusive immutable intent; exact bytes/fingerprint; six competing processes; prior-intent payload conflict; crash after file sync before send; lost create/link with stale reads; repeated real WorkService link never resends; malformed/symlink/hardlink/permission/replaced file or directory refusal; direct ledger-free mutation refusal. |
| PN-04 | Explicit disjoint groups and terminal reversal refusal; only state patched; exact-URL reuse preserves authored links/description; duplicates and foreign link identity refuse; shared finish gates remain intact. |
| PN-05 | Common named discovery/select/save/apply, stale account/project/state/authored-plan refusal; packaged selected-alias guidance; unselected Plane absence has no effect on GitHub/Jira registration; available kind exposed through public registry discovery. |

Initial tests failed before provider modules existed. Subsequent failing cases
exposed incompatible find/link wire responses, missing central registration,
ambiguous generated markers, missing common setup/guidance, malformed non-object
responses, public discovery omission, and boolean equality accepting tampered
intent schema. Required-write guards were implemented after their failures; the
final targeted run, including the inherited repaired Jira and component cases,
reported **167 passed in 2.03 seconds**.

## Required validation

All five required checks passed in the corrected Python 3.12.11 environment:
generated, format, lint, types and **1,305 tests in 225.31 seconds**. All **18**
OpenSpec items passed strict validation. The ignored receipt
`.ai-dlc/local/plane-required.json` records revision
`03f8c37d75cbc11752a4e97d975dc4428dd7b39f`, `dirty=true`, target `local`, engine
`0.4.0`. This is a frozen pre-commit source/test receipt, not a clean merged-CI or
platform receipt. Only this evidence paragraph and task-check metadata were added
after validation; tested code, tests, metadata, guidance and runbook stayed fixed.

## Integration and remaining evidence

The toolset worker independently delivered a `plane` definition with lifecycle
unavailable. Integration must coalesce its Plane definition/component/guide with
this implementation, preserve the new definition metadata fields, and adapt
TC-02's unavailable-adapter test to an explicitly unavailable fixture definition.
The original historical toolset evidence remains accurate; append prospective
adapter evidence rather than rewriting that result. An ignored coordinator patch
contains those targeted scenario/test changes; no toolset checkout was edited.

The tested contract is current public Plane work-items documentation plus public
source revision `1fec307f91003df96351557af32ce87891a3678a`. This is not an installed
version/edition or hosted release certification. HTTP loopback support is fixture
verified; a real local deployment, API/web-origin association, account scopes,
permissions, state policies, HTML sanitization, replica behavior, proxy/TLS and
live tracker swap remain unverified. #20/#21 live qualification remains open.

The local immutable-intent guarantee depends on preserving the same root/state
namespace and operation identity. Relocation, another machine, removed state or
manufactured operation IDs do not retain prior uncertainty knowledge. Neither
external pairs nor URL prechecks establish cross-machine atomic uniqueness.
Unresolved outcomes stay blocked without a reset/force-retry API. Independent
review, integration, archive/PR/merge, merged-CI and work finish remain parent-owned.


## Independent review repairs

Review of ab274c3 found that a newer reconciliation GET could reveal cancelled,
completed or unknown state after the initial transition guard, yet still authorize
a PATCH. It also found that opening an existing FIFO intent could block before
the regular-file check in both begin and verify. Both findings reproduced before
implementation: three state-change cases sent an invalid write and two bounded
subprocess cases timed out, while two valid reconciliation cases already passed.

The transition guard now validates the initial item and every fresh reconciliation
result. A newly cancelled/unknown state or a completed-to-started reversal refuses
without PATCH; a later retry cannot turn the retained intent into a fresh sender.
Already-completed and lost-response completion reconcile read-only as before.
This closes discarded-observation errors, not the unavoidable server-side interval
between the final read and PATCH; no compare-and-swap API is claimed.

Both existing-intent open paths now include O_NONBLOCK before the unchanged
descriptor type/owner/link/inode/byte checks. Two real bounded subprocess tests
create FIFOs without writers, require prompt unsafe-storage refusal, preserve
the FIFO, and verify the directory lock was released for another operation. No
path-only precheck, replacement, deletion or retry/reset API was added.

The repaired Plane provider, common onboarding, shared WorkService and component
suite passed **95 tests in 2.25 seconds** (including seven new cases). Repository
format/lint and prepared-interpreter type checks passed; `git diff --check` passed.
The existing Python 3.12.11 environment was reused. No bootstrap/download, full
package build or full suite was repeated under the coordinator's disk constraint.
These are local transport/filesystem fixtures, not live Plane qualification. Narrow
independent repair review and integrated required checks remain coordinator-owned.
