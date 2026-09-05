# Release verification

Current planning context (2026-09-05): the [framework roadmap](roadmap.md) is the
forward delivery sequence. Historical evidence below remains scoped to its stated
revision and environment. References to missing Linear mappings in the enrollment
candidate describe that earlier run; the planning branch now has a configured
sandbox connection and backlog tickets. New plans/specifications do not establish
runtime capability, live qualification, or release readiness.

This checkout is an implementation candidate, not a published or certified cross-platform release. Native Apple silicon source bootstrap from both the development worktree and a disposable clean clone, repeated setup, language fixtures, lint/type checks, strict OpenSpec validation, a hash-constrained isolated wheel installation, the final integrated required checks, and independent source review have passed. Pull request #1's expanded matrix passed on Ubuntu 24.04 and 26.04 for x64 and ARM64 plus macOS Intel. Each job published a distinct clean receipt for the same synthetic merge revision with all five required checks passing.

Outstanding: factory-clean Apple silicon setup; actual Codex Cloud and Claude Cloud hosted lifecycles; live client hook sessions; full live provider mutation conformance; behavioral skill evaluations; publication of verified release artifacts.

Docker Desktop on Apple silicon built the provider-test image from the attested official uv 0.9.11 image pinned at `sha256:4ffead4f5157cc458bbd7722122f2424c17f45eb4491fe4b34529942166aa355`. The digest-addressed image then passed the production runner's offline isolation path and 56 packaged provider/workflow checks with networking disabled. The live runner passed its namespace-firewall/direct-egress/undeclared-host preflight and then successfully read an existing issue from the designated `sandbox-aidlc` Linear team only through the exact-host allowlist proxy. The receipt identified the exact sandbox team and health reference and reported `scope = read-only-health`; full mutation conformance remains explicitly unavailable. Bootstrap release mode refuses absent wheel manifests rather than using invented URLs or hashes.

Machine provisioning and personal-agent integration pass deterministic local integration tests, including preview, owned updates, collision/drift refusal, runtime activation, and environment-reference-only credentials. A live client walkthrough is still outstanding. See the implementation record for reviewed boundaries. A disposable work-cycle walkthrough in `sandbox-aidlc` created one Linear issue, proved idempotent publish, bound a Git branch, transitioned the issue to In Progress, read the canonical remote state, and proved completion remained blocked before PR merge and merged-revision CI. After merge, completion authenticated the merged revision, downloaded and validated all five platform receipts from the successful target-branch run, and only then transitioned the sandbox issue to Done. No production Linear workspace was accessed and no package publication was performed.

A disposable clean clone completed the declared devcontainer post-create bootstrap and all required checks on Linux ARM64. Its project virtual environment is isolated in a per-devcontainer named volume so Linux executables cannot replace the host checkout's `.venv`. The Codex Cloud setup and maintenance entry scripts and the Claude Cloud setup entry script also completed in that clean Linux container; this validates their bootstrap behavior only, not either hosted platform's authentication, persistence, or network lifecycle.

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
