# Release verification

Delivery status reconciled September 10, 2026: the [roadmap](roadmap.md) and
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

Unchanged since the September 12 reconciliation: clean-machine, container and
cloud walkthroughs; full live provider mutation conformance with enforced egress;
[behavioral skill evaluations](verification/skill-evaluation.md) at the declared model and budget; publication of
verified release assets and the `verify-published` outcome for a real tag; live
Plane deployment qualification with a substitution and interruption rehearsal;
and live Jira deployment and workflow qualification. Package index publication
is not planned.

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
The workflow's `verify-published` job repeats the consumer steps against the real
release on three runners once the maintainer pushes a tag; that outcome is to be
recorded here with the tag and commit. Outstanding and unchanged: clean-machine,
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

Outstanding after this reconciliation, unchanged: clean-machine, container and cloud
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
