# Release verification

See what the current release has proven on which platforms, and what remains
unqualified before you rely on it.

Release evidence was reconciled September 14, 2026; the [roadmap](roadmap.md)
owns current priority. The former qualification issues #14/#15/#16/#17/#20/#21/#22
are cancelled, not completed, so the evidence below stays outstanding.
Historical checks apply only to their stated revision and environment; plans
and fixtures do not establish live readiness.

## What a release must prove

A release is a `v<version>` tag whose `Release` workflow passes the required
checks, builds the wheel and locked constraints, and publishes the hash-bound
bootstrap assets. It then installs from the published assets on the Linux x64,
Linux ARM64 and macOS runners; see the
[release runbook](runbooks/release-publication.md).

After a verification harness failure, a successful read-only replay may establish
consumer proof for the unchanged published assets; it does not alter the original
run. Work completion is separate: `ai-dlc work finish` passes only with the
specification, merged PR and exact merged-revision CI gates. Local checks,
fixtures and plans never stand in for live platform, provider or human-evaluation
evidence.

## Outstanding

Still outstanding: clean-machine, container and cloud walkthroughs; full live
provider mutation conformance with enforced egress; and live Jira workflow
qualification per #85. That Jira record needs `work publish`, a blocked
`work finish` before merge and a closing `work finish` after merge. Plane is
unsupported, so its live qualification is no longer planned; the Linear adapter
was removed. Package index publication is not planned.

The publication and replay below satisfy asset availability, integrity and
hosted consumer evidence for v0.4.0, and nothing else on that list.

The [September 14 Jira preparation](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/verification/jira-cloud-new-work.md#walkthrough-preparation-september-14-2026)
records missing sandbox inputs and the absent live Jira mutation target.
[Native workspace and external MCP follow-up](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/verification/documentation-workflow.md#native-workspace-and-external-mcp-follow-up-september-14-2026)
adds scoped macOS evidence while retaining unavailable company, Antigravity and
cross-platform checks. Neither record qualifies Jira or Plane.

## Native Windows core boundary

The native-core Verify job exercises source code on hosted `windows-2025` with
locked Python dependencies. Its tests cover core imports, guarded local NTFS
storage, explicit command execution and a disposable adoption, setup and check
journey without POSIX shell paths. Native results are uploaded separately as
`windows-core-results`; they are not a substitute for the five full-check
receipts.

This job does not qualify Windows 11 desktop setup, PowerShell bootstrap, every
installation module, ARM64, network shares, corporate policy or Antigravity
recognition. Native installer work is
[#172](https://github.com/Sean-Koval/ai-dlc/issues/172); client and
cross-machine observations remain [#53](https://github.com/Sean-Koval/ai-dlc/issues/53).
No Windows support claim can be inferred from local skipped tests.

On September 26, 2026, [native job 108452747319](https://github.com/Sean-Koval/ai-dlc/actions/runs/36259593343/job/108452747319)
tested revision `914acb7821bfa1e3938d5f7bdbed0310e4edba64` on Windows Server
2025, AMD64, Python 3.12.10 and local NTFS: **103 passed, 5 skipped**. Native
cases exercised process locks, killed-holder recovery, junction substitution,
sharing violations, staged publication, DACL preservation, and a passing and
failing adoption journey. The five skips are Unix-only cases; no Windows safety
case was skipped. This is source-level core evidence only.

## Consumer onboarding boundary

`project onboard` is source-only in this revision; the v0.4.0 assets do not
contain it even though the package version remains 0.4.0. A consumer must use a
reviewed source checkout and its printed checkout-specific executable. The
planner is read-only: it reports target, platform, shell, clients, enrollment,
ordered actions, findings and qualification. An actionable plan is not evidence
that any recommended operation ran.

### Observed local consumer journey — September 26, 2026

A clean source checkout at `39059e984358a8e74156315ff0d2600826ddfc1c` ran the
actual CLI on macOS 15.3.2 arm64 against a disposable target with a separate
temporary HOME/XDG account. The target selected only the Antigravity client
capability and the generic preset; the experiment did not launch Antigravity.

The fresh plan exited 1 with a missing target-check finding and matched the
adoption preview arguments. Preview and apply preserved an authored
`acceptance.py`; render and setup succeeded. After adding that target-owned
check, the new plan exited 0 while retaining `qualification: not-assessed`. The
target check passed, failed after its expected behavior was changed, and passed
after restoration. All three target-required checks then passed against clean
fixture commit `92b86689f427bd638e032e00bf436b087c1a0273`.

The scripted baseline used 18 command invocations and completed in 11.921
seconds. These timings exclude source installation and human review. This
observation does not establish clean-machine installation, Linux execution,
Windows desktop setup, or native client recognition.

## Effective environment report boundary

The opt-in status export/compare and offline doctor report are source-only
additions. Installation metadata does not establish imported engine bytes,
source dirty state or native client recognition, and reports retain those
unknowns. Equal version numbers or checksums do not qualify equivalent
environments.

Fixture verification tests schema, privacy, bounded collection, comparison and
identity invalidation. It does not qualify real client authentication,
cross-machine replication or Windows desktop setup; that observation work
remains #53, and the paid comparison
[#138](https://github.com/Sean-Koval/ai-dlc/issues/138) is pending.

On September 26, 2026, clean source revision
`6155c2c9c8a50fd32cf4b0359912a37cad6d9c32` completed a thirteen-command CLI
fixture journey on macOS. It used two isolated homes and paths with spaces and
Unicode. Export and both offline doctor modes retained matching identities and
excluded private commands.

Changing the declared Python pin produced blocking drift, and both comparisons
correctly exited 1 because required provenance remained incomplete. Unknown
fields and extra arguments were refused without echoing private sentinels, and
the process and network guards recorded no forbidden attempt. The observations
cover fixture homes on one machine, not teammate machines, Windows execution or
authenticated tools.

## Published v0.4.0 evidence — September 14, 2026

The release implementation was delivered in
[PR #88](https://github.com/Sean-Koval/ai-dlc/pull/88), merged September 13 at
`f1becc4b417622a8ca1853275c562c5ce1f90df0`.
[Verify run 34771458251](https://github.com/Sean-Koval/ai-dlc/actions/runs/34771458251)
passed all five configured platforms; each downloaded receipt names that exact
merge, reports a clean tree, and passes all eight required checks. Its archived
delivery item 9.3 remained unchecked, so the `release-publication` work record
is linked to a corrective follow-up with its own merge and fresh receipts.

The [v0.4.0 release](https://github.com/Sean-Koval/ai-dlc/releases/tag/v0.4.0)
was published at 05:27:15 UTC from tag commit
`cace021895330ae74a5f344ed5630c25547001de`.
[Release run 34809544011](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809544011)
passed `package` and `publish`; the overall run failed because all three
`verify-published` jobs failed. The successful read-only replay below provides
the consumer evidence against the same published bytes.

Before publication, [candidate run 34809155596](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809155596)
passed package checks, build and constrained wheel installation.
[Main Verify run 34809148728](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809148728)
passed all five jobs at the same source commit.

Eight assets were published: `ai_dlc-0.4.0-py3-none-any.whl`,
`ai_dlc-0.4.0.tar.gz`, `requirements.txt`, `release.sh`, `bootstrap.sh`,
`versions.sh`, `download.sh`, and `SHA256SUMS`. An independent download verified
all seven entries in `SHA256SUMS`. The manifest binds these SHA-256 digests.

| Asset | SHA-256 |
| --- | --- |
| Wheel | `246c6322c219921542fa31bd9529be0ea8578787dc90cc52ae86313e1e6906de` |
| Hashed constraints | `1287f22a7b96b8b13112b23bb8cfcfcd51831badfcc906c1df2ebfb4ac1ab26a` |
| Manifest | `40270bf873fa9b4355f01b9ac69c2b18f651883097019bf7f78d84c0712d4ae1` |

The consumer logs establish only the following:

| Hosted runner | Observed result |
| --- | --- |
| [Ubuntu 24.04 x64](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809544011/job/103868395800) | Shell checksums passed and ai-dlc 0.4.0 installed; seed setup failed with `generated project files are stale; render and commit before CI`. |
| [Ubuntu 24.04 ARM64](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809544011/job/103868395798) | Same checksum, installation and seed-setup outcome as x64. |
| [macOS 15](https://github.com/Sean-Koval/ai-dlc/actions/runs/34809544011/job/103868395774) | GitHub returned HTTP 500 while downloading `release.sh`; installation was not reached. |

The Linux seed contains only `schema = 4` and bootstrap files. Its first setup
with `--target github-actions` therefore invoked the generated-file freshness
check before those files existed. All three jobs stopped before generating and checking
`/tmp/demo`. The [runbook](runbooks/release-publication.md) describes the
read-only replay that preserves the published tag and asset bytes.

An isolated on-host check against the published assets reproduced the seed CI
failure and succeeded with local first-use setup. The released engine generated a
demo with a byte-identical manifest and its release-mode bootstrap completed.
Its three required checks passed, but the demo was nested inside the source
repository, so that check is not standalone consumer evidence.

The first [read-only replay, run 34810385278](https://github.com/Sean-Koval/ai-dlc/actions/runs/34810385278),
correctly skipped package and publication. All three runners completed seed and
demo bootstrap, then failed final checks because `/tmp/demo` had no Git
repository. The corrected fixture initializes and commits its own repository
after setup, preserving the receipt's revision identity.

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

Every job downloaded the release bootstrap assets from GitHub, verified all four
shell-file digests, installed the hash-bound wheel and constraints, and
initialized the seed. The released engine reported `release_manifest: included`
when generating the Python demo, and the byte comparison passed. The demo's
release-mode bootstrap completed, its Git fixture was committed, and
`ai-dlc project check --required --target github-actions` passed `generated`,
`work-records` and `language-check`. All three receipts reported
`engine_version: 0.4.0` and `dirty: false`.

This satisfies verified asset publication, published-asset installation on the
three hosted platforms, manifest propagation, and generated Python project
bootstrap and check evidence. A hosted runner with preinstalled tools is not a
factory-clean machine or container. Cloud-client walkthroughs, live provider
mutation and deployment qualification, and declared-model skill results with
human review remain outstanding.

## Release publication path — September 13, 2026

The [release runbook](runbooks/release-publication.md) describes publication. A
`v<version>` tag runs the `Release` workflow, which refuses a tag that does not
match `pyproject.toml`. It runs the required checks, builds the wheel and locked
hashed constraints, and verifies wheel installation and scaffolding. It then
writes the hash-bound `release.sh`, publishes the assets with the bootstrap
scripts and `SHA256SUMS`, and installs from them on three hosted runners.

Release-mode bootstrap keeps `release.sh` beside the installed engine, and
`project init` or `adopt` writes it into generated projects as
`bootstrap/release.sh`.

### Local proof against a stand-in host

Local proof on the `release-publication` branch (working tree on `67247ad`,
macOS 15.3.2 on Apple silicon) used a fresh bootstrap home and `HOME`. The
`PATH` held only system directories, and a local HTTPS server on
`localhost:8443` stood in for the release host.

- The wheel, source distribution, constraints, `release.sh`, `bootstrap.sh`,
  `versions.sh` and `download.sh` were built from the working tree and listed in
  `SHA256SUMS`. A consumer directory downloaded the four shell files and the
  checksum list and verified them (`shasum -a 256 -c`: four `OK`).
- With only `ai-dlc.toml` (`schema = 4`) beside them, `sh scripts/bootstrap.sh`
  downloaded uv, managed Python 3.12.11 and mise at their pinned digests,
  downloaded and verified the wheel and constraints, installed the engine, and
  completed project setup. The first attempt had failed because setup activated
  mise against an absent `.mise.toml`; setup now activates tools only when the
  project declares them.
- `engine-0.4.0/release.sh` was byte-identical to the served manifest.
- `ai-dlc project init <dir> --preset python` from that engine reported
  `"release_manifest": "included"` and wrote `bootstrap/release.sh` byte-identical
  to the served manifest, among 40 generated files.
- The generated project's own `scripts/bootstrap.sh` ran in release mode from
  the included manifest, and `ai-dlc project check --required` in that project
  passed `generated`, `work-records` and `language-check`. The receipt records a
  dirty tree because first setup creates the lockfile, as the template says.

This is on-host proof of the release-mode path against a local stand-in, not a
published release, a factory-clean machine or a hosted-client session. The
September 14 publication, failed attempts and successful replay above are
separate evidence against the real release.

## Cancelled change reconciliation — September 12, 2026

The OpenSpec change directories for `portable-development-v4`,
`portable-tracker-adapters` and `selective-tracker-migration` were archived to
their delivered scope, so `openspec list` no longer presents cancelled work as
active. Their requirements entered the specification baseline as
`portable-development`, `portable-tracker-adapters` and
`selective-tracker-migration`.

Archiving records obligations, not qualification. A baseline requirement states
what the system SHALL do; the evidence for what was actually proven stays in this
document and in `verification/`. Nothing outstanding became satisfied. Each
archived task list keeps its unperformed steps under an explicit "Deferred live
qualification — not delivered" heading. The requirements themselves say that
fixture tests are not live platform verification.

`portable-tracker-adapters` had no work record and no tracker item, so it could
not be completed through `ai-dlc work finish`. It was reconciled as a
documentation-only archive rather than through a retrospective work record. Its
delivered substance was finished through its children, archived on 2026-09-08
as `jira-cloud-new-work` and `plane-new-work`.

## Earlier evidence

Dated records from September 4 through September 8, 2026 and the candidate manifest
preparation notes are in the
[release verification history](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/verification/release-history.md).
