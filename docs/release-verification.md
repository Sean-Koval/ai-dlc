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
runners; see the [release runbook](runbooks/release-publication.md). Work
completion is separate: `ai-dlc work finish` passes only with the specification,
merged PR and exact merged-revision CI gates. Local checks, fixtures and plans
never stand in for live platform, provider or human-evaluation evidence.

## Outstanding

Clean-machine, container and cloud walkthroughs; full live provider mutation
conformance with enforced egress; behavioral skill evaluations at the declared
model and budget, including human review; a successful `verify-published` outcome
for a real tag; live Plane deployment qualification with a substitution and
interruption rehearsal; and live Jira deployment and workflow qualification remain
outstanding. Package index publication is not planned. The publication below
satisfies asset availability and integrity evidence; its failed consumer checks
do not establish a qualified release.

## Published assets and failed consumer checks — September 14, 2026

The [v0.4.0 release](https://github.com/Sean-Koval/ai-dlc/releases/tag/v0.4.0)
was published at 05:27:15 UTC from tag commit
`cace021895330ae74a5f344ed5630c25547001de`.
[Release run 34809544011](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809544011)
passed `package` and `publish`; the overall run failed because all three
`verify-published` jobs failed. This is publication evidence, with consumer
qualification still incomplete.

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
replay that preserves the published tag and asset bytes. Hosted replay results
remain pending.

An isolated on-host recovery check against these real published assets then
reproduced the seed CI failure and succeeded with local first-use setup. On
macOS, separate bootstrap and mise data directories kept the shared aliases
unchanged. The released engine generated a demo with a byte-identical
manifest; the demo's release-mode bootstrap completed, followed by all three
required checks (`generated`, `work-records`, `language-check`) with explicit
`--target github-actions`. This establishes the package's working first-use path
on that host. It is separate from the failed hosted jobs and does not establish
the outstanding container or three-platform hosted evidence.

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
The September 14 publication and failed hosted consumer checks above are
separate evidence against the real release. Outstanding and unchanged: clean-machine,
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
