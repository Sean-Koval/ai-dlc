# Release verification

Delivery status reconciled September 10, 2026: the [roadmap](roadmap.md) and
[GitHub issues](https://github.com/Sean-Koval/ai-dlc/issues) own current priority.
PR28 is merged; former qualification/publication issues #14/#15/#16/#17/#20/#21/#22
are cancelled (NOT_PLANNED), not completed. Outstanding release evidence below
remains outstanding despite cancellation. Historical checks apply only to their
stated revision and environment; plans and fixtures do not establish live readiness.

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

## Historical source delivery — September 8, 2026

PR25 merged at `ab6b774`; all five exact merged-revision receipts passed. A fresh
GitHub clone completed source bootstrap, then gated finish completed issues10
and11. This is fresh-clone evidence on the existing host, not factory-clean or
work-laptop qualification. See the [current integration record](verification/work-computer-toolsets.md)
for PR26, including the packaging correction, onboarding repairs and exact-source
checks. Its GitHub delivery status and gated finish are separate from the remaining
platform, native-client, live-provider and human-evaluation qualifications.

This checkout is an implementation candidate, not a published or certified cross-platform release. Native Apple silicon source bootstrap from both the development worktree and a disposable clean clone, repeated setup, language fixtures, lint/type checks, strict OpenSpec validation, a hash-constrained isolated wheel installation, the final integrated required checks, and independent source review have passed. Pull request #1's expanded matrix passed on Ubuntu 24.04 and 26.04 for x64 and ARM64 plus macOS Intel. Each job published a distinct clean receipt for the same synthetic merge revision with all five required checks passing.

Outstanding: factory-clean Apple silicon setup; actual Codex Cloud and Claude Cloud hosted lifecycles; live client hook sessions; full live provider mutation conformance; behavioral skill evaluations; publication of verified release artifacts.

Docker Desktop on Apple silicon built the provider-test image from the attested official uv 0.9.11 image pinned at `sha256:4ffead4f5157cc458bbd7722122f2424c17f45eb4491fe4b34529942166aa355`. The digest-addressed image then passed the production runner's offline isolation path and 56 packaged provider/workflow checks with networking disabled. The live runner passed its namespace-firewall/direct-egress/undeclared-host preflight and then successfully read an existing issue from the designated `sandbox-aidlc` Linear team only through the exact-host allowlist proxy. The receipt identified the exact sandbox team and health reference and reported `scope = read-only-health`; full mutation conformance remains explicitly unavailable. Bootstrap release mode refuses absent wheel manifests rather than using invented URLs or hashes.

Machine provisioning and personal-agent integration pass deterministic local integration tests, including preview, owned updates, collision/drift refusal, runtime activation, and environment-reference-only credentials. A live client walkthrough is still outstanding. See the implementation record for reviewed boundaries. A disposable work-cycle walkthrough in `sandbox-aidlc` created one Linear issue, proved idempotent publish, bound a Git branch, transitioned the issue to In Progress, read the canonical remote state, and proved completion remained blocked before PR merge and merged-revision CI. After merge, completion authenticated the merged revision, downloaded and validated all five platform receipts from the successful target-branch run, and only then transitioned the sandbox issue to Done. No production Linear workspace was accessed and no package publication was performed.

A disposable clean clone completed the declared devcontainer post-create bootstrap and all required checks on Linux ARM64. Its project virtual environment is isolated in a per-devcontainer named volume so Linux executables cannot replace the host checkout's `.venv`. The Codex Cloud setup and maintenance entry scripts and the Claude Cloud setup entry script also completed in that clean Linux container; this validates their bootstrap behavior only, not either hosted platform's authentication, persistence, or network lifecycle.

## Remaining-issue qualification candidate — September 8, 2026

The [setup continuity record](verification/setup-continuity.md) adds actual native
and network-disconnected container observations at clean `189913b`. Its report
keeps complete Q-01–03 qualification unmet. Migration target creation/recovery
and Design PM experiment inputs are separate reviewed implementation work;
neither establishes authenticated provider conformance or human-rated benefit.
No release assets have been published.

## Portable profile enrollment candidate — 2026-09-04

The source bootstrap completed in the linked implementation worktree. The reviewed
`portable-profile-enrollment` work record parsed through the locked project
environment and remained local with no tracker artifact. Existing ignored sandbox
probe metadata identifies the designated sandbox team but does not contain the
native workflow status IDs required by the work service. No Linear publication,
transition, discovery, or other remote mutation was attempted; provider publication
is deferred to the provider-onboarding cycle.

A disposable Git repository outside the checkout was populated from
`profiles/example/ai-dlc-profile.toml` and exercised with temporary XDG config,
cache, and state roots. Enrollment preview left active state unchanged. Enrollment
apply created only the isolated schema-1 lock and schema-4 machine file. Status then
reported `example-development`, a 40-character pinned commit, a healthy cache, and
the expected unbound `linear-sandbox` requirement. Machine plan used the same locked
commit, remained a preview, and reported clean agent configuration. The local source
was correctly classified as nonportable, the immutable cache contained only the
declared profile file, `HOME` was not replaced, no machine apply targeted the real
user home, and the disposable directory was removed after evidence capture.

Packaging and security verification built both the source distribution and the real
`ai_dlc-0.4.0-py3-none-any.whl`. The focused credential, enrollment, profile-source,
machine, and machine-integration suite passed 252 tests; the final review's affected
configuration, profile-source, CLI, and template suite passed 497 tests; generated-file
drift checks passed. The bounded token-setting compatibility correction then passed
23 focused config/cache security cases, all 186 configuration and profile-source tests,
and 163 affected lifecycle tests. Initial wheel inspection found that the prior
directory-wide profile asset rule still included the legacy user-named profile. A
regression-first packaging fix limited the wheel to the base profile and the two
approved public examples, and the final review applied the same exclusion to the
source distribution.
The rebuilt wheel contains 741 members and the rebuilt source distribution contains
1,474 members. Each contains exactly the three approved public profile assets and no
`.ai-dlc/local` state, enrollment lock, unexpected machine binding, environment file,
Git metadata, legacy user-named profile, checkout path, or user-specific content
marker.

The required project gate ran through the bootstrap PATH and locked environment with
its receipt written under ignored `.ai-dlc/local/`. All five required outcomes passed:
generated, format, lint, types, and 785 tests. The portable enrollment OpenSpec change
was strictly validated while active, archived at
`openspec/changes/archive/2026-09-03-portable-profile-enrollment/`, and promoted to a
strictly valid canonical capability spec. The work record now resolves that exact
archive path. This is pre-commit local candidate evidence; the receipt correctly
records a dirty checkout and does not establish merged-revision CI.

This evidence does not qualify a factory-clean machine, either hosted cloud runtime,
provider onboarding or discovery, Obsidian create/attach, behavioral skill quality,
live client sessions, published package assets, or release readiness. The
complete-branch independent review is complete; PR checks, merge, and merged-revision
verification remain separate integration gates.

## GitHub ticket workflows candidate — 2026-09-07

The GitHub-first child implements capability-based work start, Issues/Projects,
named setup that defaults to a repository-associated Project, and selected/default
tracker migration with bounded local recovery. Clean candidate `29b67b3` passed
all required checks with 1,138 tests. Independent implementation and activation
reviews accepted the candidate. All five platform jobs passed at `332f5b0` in
run `34162136610` for PR #23.

Live setup reused and verified Project #2's repository link. The default tracker
switch and eight selected existing-ticket mappings applied with durable receipts.
A disposable live issue exercised attachment recovery, a lost start response,
direct close/reopen/reconciliation and the real refusal to finish an unmerged PR.
The disposable issue was closed and removed from the board. These operations do
not establish a successful gated finish or crash-atomic recovery. The two behavior
specifications are archived locally and promoted to canonical specs; final archive
review passed, PR #23 merged631d10a, and all five target-branch receipts were
authenticated before AI-DLC work finish completed #18 from a clean clone. That
clone used the existing provisioned host; factory-clean and actual-client
qualification remain separate.

See the [detailed qualification record](verification/github-ticket-workflows.md).
Linear inventory reconciliation is deferred by the maintainer. Jira/Plane,
Antigravity, bundle cleanup and package publication are separate deliverables.

## Candidate manifest preparation

The manual release verification workflow accepts an explicit intended HTTPS artifact
base URL and produces `release.sh` alongside the built wheel and hashed
`requirements.txt`. The generator validates the wheel filename and embedded engine
name/version, refuses ambiguous wheels or existing output, and records actual file
hashes. Candidate generation neither uploads assets to that URL nor establishes
that the destination exists. After separately authorized publication and download
verification, the reviewed manifest belongs at `bootstrap/release.sh` in the
bootstrap distribution. Source development continues to use `--source`.

Release-mode shell fixtures exercise successful selection/setup and tampered
wheel/constraints refusal before engine installation. The tool/package transport
boundaries are fixtures; they do not establish live artifact hosting or wheel
installation. The manual workflow retains its real isolated wheel installation
against exported hashed constraints before preparing the candidate manifest.
