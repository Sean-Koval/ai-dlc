# Release verification

Release evidence reconciled September 14, 2026: the [roadmap](roadmap.md) and
[GitHub issues](https://github.com/Sean-Koval/ai-dlc/issues) own current priority.
PR28 is merged; former qualification/publication issues #14/#15/#16/#17/#20/#21/#22
are cancelled (NOT_PLANNED), not completed. Outstanding release evidence below
remains outstanding despite cancellation. Historical checks apply only to their
stated revision and environment; plans and fixtures do not establish live readiness.

## What a release must prove

A release is a `v<version>` tag whose `Release` workflow passes the required checks,
builds the wheel and locked constraints, publishes the hash-bound bootstrap assets,
and installs from the published assets on the Linux x64, Linux ARM64 and macOS
runners; see the [release runbook](runbooks/release-publication.md). After a
verification harness failure, a successful read-only replay may establish consumer
proof for the unchanged published assets; it does not alter the original run. Work
completion is separate: `ai-dlc work finish` passes only with the specification,
merged PR and exact merged-revision CI gates. Local checks, fixtures and plans
never stand in for live platform, provider or human-evaluation evidence.

## Outstanding

Clean-machine, container and cloud walkthroughs; full live provider mutation
conformance with enforced egress; [behavioral skill evaluations](verification/skill-evaluation.md)
at the declared model and budget, including human review; live Plane deployment qualification
with a substitution and interruption rehearsal; and live Jira deployment and workflow qualification remain
outstanding. Package index publication is not planned. The publication
and successful replay below satisfy asset availability, integrity and hosted
consumer evidence for v0.4.0. They do not satisfy those remaining walkthroughs or
provider and human-evaluation obligations.

The [September 14 Jira preparation](verification/jira-cloud-new-work.md#walkthrough-preparation--september-14-2026)
records missing sandbox inputs and the absent live Jira mutation target.
[Native workspace and external MCP follow-up](verification/documentation-workflow.md#native-workspace-and-external-mcp-follow-up--september-14-2026)
adds scoped macOS evidence while retaining unavailable company, Antigravity and
cross-platform checks. Neither record qualifies Jira or Plane.

## Native Windows core boundary

The native-core Verify job exercises source code on hosted `windows-2025` with locked Python dependencies. Its tests cover core imports, guarded local NTFS storage, explicit command execution and a disposable adoption/render/setup/check journey with POSIX shell paths removed. The existing Unix required-check jobs remain in the same workflow. Native test results are uploaded separately as `windows-core-results`; they are not a substitute for the five configured full-check receipts.

This job does not qualify Windows 11 desktop setup, PowerShell bootstrap, every installation module/provider, ARM64, network shares, corporate policy or Antigravity recognition. Native installer work is [#172](https://github.com/Sean-Koval/ai-dlc/issues/172), and actual client/cross-machine observations remain [#53](https://github.com/Sean-Koval/ai-dlc/issues/53). Plane's private mutation-intent store, vendored workflow-bundle APIs and descriptor-only document inventory traversal explicitly refuse unsupported native operations. Historical v0.4.0 published assets remain unchanged. No Windows support claim can be inferred from local skipped tests.

## Published v0.4.0 evidence — September 14, 2026

The original release implementation was delivered in
[PR #88](https://github.com/Sean-Koval/ai-dlc/pull/88), merged September 13 at
`f1becc4b417622a8ca1853275c562c5ce1f90df0`.
[Verify run 34771458251](https://github.com/Sean-Koval/ai-dlc/actions/runs/34771458251)
passed all five configured platforms; each downloaded receipt names that exact
merge, reports a clean tree, and passes all eight required checks. Its archived
delivery item 9.3 remained unchecked, so the original `release-publication` work
record is linked to a corrective follow-up that finalizes this evidence. The
original PR and merge remain historical provenance; normal work finish still
requires the follow-up's own merge and fresh merged-revision CI receipts.

The [v0.4.0 release](https://github.com/Sean-Koval/ai-dlc/releases/tag/v0.4.0)
was published at 05:27:15 UTC from tag commit
`cace021895330ae74a5f344ed5630c25547001de`.
[Release run 34809544011](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809544011)
passed `package` and `publish`; the overall run failed because all three
`verify-published` jobs failed. The later successful read-only replay below
provides the consumer evidence against the same published bytes.

Before publication, [candidate run 34809155596](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809155596)
passed package checks, build, constrained wheel installation and legacy scaffolding.
[Main Verify run 34809148728](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809148728)
passed all five configured jobs at the same source commit. The tag's package job
repeated required checks, built the wheel and source distribution, installed the
wheel against hashed constraints, and generated six legacy scaffold files.

Eight assets were published: `ai_dlc-0.4.0-py3-none-any.whl`,
`ai_dlc-0.4.0.tar.gz`, `requirements.txt`, `release.sh`, `bootstrap.sh`,
`versions.sh`, `download.sh`, and `SHA256SUMS`. An independent download from the
real release verified all seven entries in `SHA256SUMS`. The manifest names the
v0.4.0 release download URLs and binds these exact SHA-256 digests:

| Asset | SHA-256 |
| --- | --- |
| Wheel | `246c6322c219921542fa31bd9529be0ea8578787dc90cc52ae86313e1e6906de` |
| Hashed constraints | `1287f22a7b96b8b13112b23bb8cfcfcd51831badfcc906c1df2ebfb4ac1ab26a` |
| Manifest | `40270bf873fa9b4355f01b9ac69c2b18f651883097019bf7f78d84c0712d4ae1` |

The consumer logs establish only the following:

| Hosted runner | Observed result |
| --- | --- |
| [Ubuntu 24.04 x64](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809544011/job/103868395800) | Shell checksums passed and AI-DLC 0.4.0 installed; seed setup failed with `generated project files are stale; render and commit before CI`. |
| [Ubuntu 24.04 ARM64](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809544011/job/103868395798) | Same checksum, installation and seed-setup outcome as x64. |
| [macOS 15](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809544011/job/103868395774) | GitHub returned HTTP 500 while downloading `release.sh`; installation was not reached. |

The Linux seed contains only `schema = 4` and bootstrap files. Running its first
setup with `--target github-actions` invokes the generated-file freshness check
before those files exist. All three jobs stopped before generating and checking
`/tmp/demo`. Neither a clean-container walkthrough nor a successful three-platform
consumer run can be inferred from these failures. Recovery retains the failed run's identity; the [runbook](runbooks/release-publication.md) describes a read-only
replay that preserves the published tag and asset bytes.

An isolated on-host recovery check against these real published assets then
reproduced the seed CI failure and succeeded with local first-use setup. On
macOS, separate bootstrap and mise data directories kept the shared aliases
unchanged. The released engine generated a demo with a byte-identical
manifest and the demo's release-mode bootstrap completed. Its three required
checks passed, but the demo was nested inside the source repository and its
receipt inherited that parent's Git revision. That check is not standalone
consumer evidence.

The first [read-only replay, run 34810385278](https://github.com/Sean-Koval/ai-dlc/actions/runs/34810385278),
at workflow commit `82845700dc9eefea8135df1a9c8b5335abd7815c`, correctly skipped
package and publication. All three hosted runners completed seed and demo
bootstrap, then failed final checks because `/tmp/demo` had no Git repository.
The corrected fixture initializes and commits its own Git repository after setup
before checking, preserving the receipt's required revision identity. A successful
standalone hosted replay then passed as recorded below.

### Successful read-only hosted replay

[Release replay 34810567728](https://github.com/Sean-Koval/ai-dlc/actions/runs/34810567728)
passed on September 14, 2026 using workflow commit
`74fd6bf6bc08c158440aba4d277b7fa2821d3834`, with `verify_published_tag=v0.4.0`.
`package` and `publish` were skipped. The release tag still resolves to
`cace021895330ae74a5f344ed5630c25547001de`; no package was rebuilt and no asset or
tag was replaced.

| Consumer job | Runner image version | Clean demo receipt commit |
| --- | --- | --- |
| [Linux x64, Ubuntu 24.04](https://github.com/Sean-Koval/ai-dlc/actions/runs/34810567728/job/103870914729) | `20260907.300.1` | `f0d8bd20bda293a254f165ad96a075c463c16bc8` |
| [Linux ARM64, Ubuntu 24.04](https://github.com/Sean-Koval/ai-dlc/actions/runs/34810567728/job/103870914640) | `20260907.118.1` | `aa834101d329d171297ac38013f483db4b520cc1` |
| [macOS 15 ARM64](https://github.com/Sean-Koval/ai-dlc/actions/runs/34810567728/job/103870914686) | `20260907.0337.1` | `14f3c441189472d9584991d80cfcd683b78ce664` |

Every job downloaded the existing release bootstrap assets from GitHub, verified
all four shell-file digests, installed the hash-bound wheel and constraints, and
initialized the seed. The released engine reported `release_manifest: included`
when generating the Python demo; the workflow's byte comparison passed. The
demo's own release-mode bootstrap completed, its independent Git fixture was
committed, and `ai-dlc project check --required --target github-actions` passed
`generated`, `work-records`, and `language-check`. All three receipts reported
`engine_version: 0.4.0` and `dirty: false`.

This satisfies verified release asset publication, published-asset installation
on the three named hosted platforms, manifest propagation, and generated Python
project bootstrap/check evidence. The original publication workflow and first
replay remain failed historical runs. A hosted runner with preinstalled tools is
not a factory-clean machine or clean container; cloud-client walkthroughs, live
provider mutation and deployment qualification, and declared-model skill results
with human review remain outstanding. No package-index publication is claimed.

## Release publication path — September 13, 2026

The [release runbook](runbooks/release-publication.md) now describes publication:
a `v<version>` tag runs the `Release` workflow, which refuses a tag that does not
match `pyproject.toml`, runs the required checks, builds the wheel and locked
hashed constraints, verifies wheel installation and scaffolding, writes the
hash-bound `release.sh` against the release download directory, publishes those
assets plus the three bootstrap scripts and `SHA256SUMS`, and then installs from
the published assets on Linux x64, Linux ARM64 and macOS runners. Release-mode
bootstrap keeps `release.sh` beside the installed engine, and `ai-dlc project
init` or `adopt` writes it into generated projects as `bootstrap/release.sh`; a
source-installed engine reports the manifest as absent.

Local proof on the `release-publication` branch (working tree on `67247ad`,
macOS 15.3.2 on Apple silicon), with a fresh bootstrap home, a fresh `HOME`, a
`PATH` holding only system directories, and a local HTTPS server on
`localhost:8443` standing in for the release host (self-signed certificate
supplied through `CURL_CA_BUNDLE`):

- The wheel, source distribution, constraints, `release.sh`, `bootstrap.sh`,
  `versions.sh` and `download.sh` were built from the working tree and listed in
  `SHA256SUMS`. A consumer directory downloaded the four shell files and the
  checksum list and verified them (`shasum -a 256 -c`: four `OK`).
- With only `ai-dlc.toml` (`schema = 4`) beside them, `sh scripts/bootstrap.sh`
  downloaded uv, managed Python 3.12.11 and mise at their pinned digests,
  downloaded and verified the wheel and constraints from the stand-in host,
  installed the engine, and completed project setup. The first attempt had
  failed here because setup activated mise against an absent `.mise.toml`;
  setup now activates tools only when the project declares them.
- `engine-0.4.0/release.sh` was byte-identical to the served manifest.
- `ai-dlc project init <dir> --preset python` from that engine reported
  `"release_manifest": "included"` and wrote `bootstrap/release.sh` byte-identical
  to the served manifest, among 40 generated files.
- The generated project's own `scripts/bootstrap.sh` ran in release mode from
  the included manifest, and `ai-dlc project check --required` in that project
  passed `generated`, `work-records` and `language-check`. The receipt records a
  dirty tree because first setup creates the lockfile, as the template says.

This is on-host proof of the release-mode path against a local stand-in, not a
published release, not a factory-clean machine and not a hosted-client session.
The September 14 publication, failed attempts, and successful read-only replay
above are separate evidence against the real release. Outstanding and unchanged: clean-machine,
container and cloud walkthroughs; full live provider mutation conformance;
behavioral skill evaluations; live Plane and Jira qualification. Package index
publication is not planned.

## Cancelled change reconciliation — September 12, 2026

The OpenSpec change directories for `portable-development-v4`, `portable-tracker-adapters`
and `selective-tracker-migration` were archived to their delivered scope, so `openspec list`
no longer presents cancelled work as active. Their requirements entered the specification
baseline as `portable-development`, `portable-tracker-adapters` and
`selective-tracker-migration`.

Archiving records obligations, not qualification. A baseline requirement states what the
system SHALL do; the evidence for what was actually proven stays in this document and in
`verification/`. Nothing outstanding above or below became satisfied, and each archived
task list keeps its unperformed steps under an explicit "Deferred live qualification — not
delivered" heading rather than marking them done. The requirements themselves carry the
distinction: portable development requires that "Local fixture tests SHALL NOT be
represented as live platform verification", TA-05 requires adapters to separate fixture,
health and live workflow evidence, and TM-04 requires unavailable source state to remain
explicitly unknown.

At the September 12 checkpoint, outstanding obligations were: clean-machine, container and cloud
walkthroughs; full live provider mutation conformance with enforced egress; behavioral
skill evaluations at the declared model and budget; publication of verified release assets;
live Plane deployment qualification with a substitution and interruption rehearsal; and
live Jira deployment and workflow qualification.

`portable-tracker-adapters` had no work record and no tracker item, so it could not be
completed through `ai-dlc work finish`. It was reconciled as a documentation-only archive
under this record rather than by creating a retrospective work record, because a new
reviewed record would imply a delivery and review cycle that never took place for the
parent. Its delivered substance was reviewed and finished through its children, whose
specifications were archived on 2026-09-08 as `jira-cloud-new-work` and `plane-new-work`.

## Earlier evidence

Dated records from September 4 through September 8, 2026 and the candidate manifest
preparation notes are in the
[release verification history](archive/verification/release-history.md).
