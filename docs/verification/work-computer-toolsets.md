# Work-computer toolsets integration

Status: reviewed integration in [PR26](https://github.com/Sean-Koval/ai-dlc/pull/26).
Exact-source checks are recorded below; GitHub owns live delivery status. This batch follows the current work-computer roadmap, not historical
Linear priorities. No company, Plane or Confluence service has been mutated.

## Reviewed components

| Component | Independently accepted source | Evidence |
| --- | --- | --- |
| Onboarding requirement integrity (#19) | `37187c7` | [Onboarding](onboarding-readiness.md) |
| Delivery traceability (#12) | `4058b24` | [Traceability](spec-delivery-traceability.md) |
| Toolset selection (#19) | `f3d74dd` | [Toolset](toolset-composition.md) |
| Native role composition (#19) | `6cb80b2` | [Native composition](native-tool-composition.md) |
| Optional Plane new work (#20 child) | `548a6dd` | [Plane](plane-new-work.md) |
| Jira Cloud new work (#20 child) | `03d5cbe` | [Jira](jira-cloud-new-work.md) |
| Conditional credential readiness (#19) | `213da0e` | [Credential readiness](credential-readiness.md) |
| Bootstrap executable publication (#14 child) | `63d6ec5` | [Bootstrap](bootstrap-executable-publication.md) |
| Qualification-record validator (#14 preparation) | `e39202b` | [Qualification](framework-qualification.md) |
| Optional Design PM (#13) | `eb04ca1` | [Design source/development review](design-pm/review.md) |
| Product evaluation preparation (#15) | `6a95a49`, `ed5f2ee` | [Preparation](product-delivery-evaluation.md) |

The credential repair closes the integrated Jira Basic false-ready finding through
trusted conditional environment requirements. Root inspected the full diff and
reran 68 credential/readiness tests: all passed. It preserves the composed provider
metadata fields and keeps readiness separate from authentication.

Design guidance received an independent source review against DP-01 through DP-06;
eight fresh distribution/preservation tests passed after integration. Calibration
preparation received a separate source review and two fresh invariant tests. Its
model-proposed decisions are not human labels, and no experiment was executed.

## Packaging and first integrated run

The first combined run passed generated/format/lint/types but failed three tests:
source cache resolution and two package/adoption cases during disk pressure. Two
failures explicitly reported no space left; the Git failure's cause was not proven.
The failed outcome remains recorded, not promoted to successful verification.

Source distributions were including the tracked legacy Rust compiler output tree.
The regression failed on actual target entries before fix `8551b09`, then the real
package check passed. The fix excludes only `/target/**` from Python source
packages; its test requires `Cargo.toml` and historical `crates/*.rs` remain present.
It neither deletes tracked source nor changes the historical Rust implementation.
Independent two-file review accepted the fix. After integration, all three earlier
failures passed together (3 tests, 6.47 seconds). That focused retry does not replace
final combined required checks.

## Completion boundaries

PR25 merged at `ab6b774`; fresh-clone gated finish completed #10 and #11 with five
exact merged-revision receipts. Live reads confirm Completed and Project Done.
This batch must independently pass required checks, finalized specs, review, PR,
merge and matching main-revision CI before its eligible issues can finish.

Actual work-laptop client recognition/authentication, installed Plane behavior,
full provider qualification, human-rated comparisons and package publication remain
separate open obligations. Local fixtures, synthetic guidance observations and
source reviews do not establish any of those results.

## Final component integration reviews

Pre-Plane integration at clean `b7d1ace` was independently accepted;132 targeted
connection, credential, native, toolset and scanner tests passed167.31seconds.
Plane initial review found two reproducible issues: stale terminal state before
PATCH and a blocking FIFO intent read. Repair `548a6dd` was independently accepted;
original reproductions now refuse promptly, no disallowed PATCH occurs, and68
focused tests passed2.57seconds. Live deployment behavior remains unverified.

The Plane merge `467de24` was independently accepted: registry and provider code
match the accepted candidate; richer Plane configuration appears once, trusted
credential/Obsidian fields remain, and the explicit unavailable-lifecycle fixture
preserves its refusal scenario. The archived Jira specification was retained.

## Clean combined source verification

At clean `4064bd9a5ca34efc4b35d9fecde7d58c194e744f`, all five required checks
passed locally: **1,772 tests, 476.71 seconds**. The
[local receipt](work-computer-toolsets/local-checks-4064bd9.json) identifies the
exact source. An earlier attempt found one import-order error in the merged
unavailable-lifecycle regression; its test phase was intentionally interrupted,
the import was corrected and all five checks were rerun. The failed/interrupted
attempt remains in the ignored execution evidence, not counted as passing.

The existing isolated Ubuntu24.04 ARM64 container was updated to the same clean
revision through Git bundles. Source bootstrap completed with target devcontainer;
all five required checks passed: **1,771 tests and one platform skip,120.43seconds**.
The [container receipt](work-computer-toolsets/container-checks-4064bd9.json)
records that exact clean revision and target. The earlier container and its
isolated virtual-environment volume were reused. This is current-source container
verification, not factory-clean setup, an actual hosted cloud session or native
Claude/Antigravity recognition.

A separate credential-free CLI walkthrough adopted a Python work repository with
Jira, Obsidian, Claude Code and Antigravity; reviewed/applied one shared local MCP
connection, rendered/checksummed both clients and preserved three authored
sentinels. Ten skills and the local server definition appeared in each client.
No native app or MCP process was launched. Missing Jira settings were reported,
and connection refused before service access. It exposed two remaining onboarding
gaps: default GitHub SCM/none-deploy catalog recognition and a concrete machine
vault-binding route. Both were repaired in independently accepted `37187c7`: SCM and inactive deployment
are recognized, actual runtime requirements survive component overrides, and the
runbook exercises existing private machine enrollment. The original override
reproduction now refuses; 157 fresh focused tests and four additional custom
component cases passed. The final integrated checks are recorded separately from
the historical 4064bd9 checks.

## Final onboarding integration verification

Clean `822a5fbfcb92a17715a33ed5ff1c9af4c58e4d8b` includes both independently
accepted onboarding commits without source changes, finalized OR-01 through OR-03
and the reviewed current delivery documentation. Fresh local affected tests passed
157 cases in 2.48 seconds; repository format, lint, types and generated checks passed.
Strict OpenSpec validation passed all 23 items. Local full-suite evidence above
continues to identify its earlier revision.

The existing isolated Ubuntu24.04 ARM64 container was updated to clean 822a5fb
and source bootstrap completed again. All five required checks passed, including
**1,802 tests and one platform skip in 108.89 seconds**. The
[final container receipt](work-computer-toolsets/container-checks-822a5fb.json)
identifies exact source, clean state and devcontainer target. The same container
and isolated environment volume were reused; no native client or live provider
qualification is implied. Subsequent documentation-only evidence commits are
covered by PR26 CI; exact merged-revision receipts remain mandatory for finish.
