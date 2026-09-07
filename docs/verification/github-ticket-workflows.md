# GitHub ticket workflow qualification

Implementation branch: `codex/github-ticket-workflows`, based on planning commit
`0775b90`. Live and fixture evidence are recorded separately.

## Live activation after CLI authorization

AI-DLC's saved default setup reused Project #2 and verified its repository link.
The default-only and eight selected-work migrations applied with durable before/
after receipts; their outcomes are `applied` with no uncertain paths. Read-back
of `github-ticket-workflows` resolves issue #18, native open, Project In Progress.
Non-tracker effective identities and all unselected work bytes were preserved.

The live disposable issue #24 exercised the production executable adapter, work
service, actual API responses and local journal. A real uncertain attachment was
reconciled using the retained issue reference. A test wrapper dropped one response
only after the actual live start succeeded; retry reconciled the same item.
The real unmerged PR blocked finish without a terminal mutation. Separate direct
adapter close/reopen/close/reconcile checks passed on the disposable issue, which
was closed and removed from the board afterward. This is not evidence of a gated
finish, infrastructure crash recovery, or the default-create path against GitHub.
The initial transient attachment mismatch's remote cause remains unproven.
Detailed scope and receipts are in the [adoption record](../planning/github-backlog-migration.md).

PR candidate `270e957` passed all five platform jobs in run `34159101762`.
This is PR candidate CI, not target-branch merged-revision evidence. Configuration,
work mappings and rendered guidance changed during activation; the earlier local
1,137-test pass does not qualify those subsequent project-file changes.

The first activation required run found one test failure: the agent-client role
regression loaded this repository's selected tracker while hardcoding Linear's
catalog and expected result. This was a fixture coupling exposed by the actual
tracker swap, not a live adapter failure. The corrected test uses explicit
schema-4 input and the packaged catalog, covers both Linear and GitHub, and
asserts no unresolved client selections. All 55 component/CLI tests pass; no
production Python behavior changed.

The corrected activation candidate `29b67b397c32840839c6e603a0681cd9a20268eb`
passed all five required checks on a clean tree (`dirty=false`), including
**1,138 tests** in 172.23 seconds. Receipt:
`.ai-dlc/local/github-activation-required-final.json`. Scoped independent review
of `270e957..29b67b3` found no P1/P2 issues, verified receipt/file correspondence,
and accepted the fixture correction and evidence boundaries. All 15 OpenSpec
items passed strict validation. Four Linux platform jobs passed for this
candidate in run `34161686184`; the macOS Intel job was still running at this
checkpoint. Subsequent documentation-only commits record this evidence without
claiming qualification for a different revision.

## September 7 Project-default follow-through

[Draft PR #23](https://github.com/Sean-Koval/ai-dlc/pull/23) publishes the candidate.
Platform checks are pending; no archive, merge or finish has occurred.

The maintainer selected the GitHub backlog as the work queue and deferred Linear
reconciliation. Thirteen issues are now in [AI-DLC Project #2](https://github.com/users/Sean-Koval/projects/2),
with verified status mappings and All work / Delivery board views. The
[adoption record](../planning/github-backlog-migration.md) separates actual MCP
Project operations from pending CLI permission, repository linking, and local
tracker activation. Earlier no-mutation/source-inventory notes below describe
prior checkpoints and are superseded by that record.

The `github-project-defaults` child implements default repository inference and
Project reuse/create, explicit issues-only setup, immutable creation retry
identity, late repository checks and authored-configuration protection. TDD
reproduced the missing behavior and review regressions before fixes. Independent
review accepted the final 47 onboarding/default tests with no remaining P1/P2
findings. Its review was local and mocked.

All five required project checks passed against the final implementation tree:
generated, format, lint, types, and **1,137 tests** in 278.03 seconds. All **15**
OpenSpec items passed strict validation. The ignored receipt
`.ai-dlc/local/project-defaults-required-final.txt` records base `b6c89aa` and
`dirty=true`, correctly identifying pre-commit candidate evidence; subsequent
edits only record qualification and delivery status. This is not clean-commit
or merged-revision CI evidence. The default-create adapter path and recovery
remain fixture-qualified; actual MCP creation does not qualify the adapter.

## Initial read-only environment inspection

On September 7, 2026, the installed CLI reported `gh version 2.95.0` (2026-06-17).
`gh api user --jq .login` returned `Sean-Koval`.
`gh project list --owner @me --format json` failed because the current credential
lacks `read:project`. No project/issue/configuration or authentication mutation
was performed. GitHub Projects read/write qualification is pending appropriate
local authentication, a selected repository and Project, and designated test data.
Do not claim project access from the successful account lookup.

The exact migration candidate mapping remains unreviewed. Local work records alone
cannot establish complete remote Linear active/planned inventory.

## Implementation evidence

Task 1 is implemented in `0834dd7`, with review fixes `e1d4382` and `e121fed`.
The initial focused provider/workflow suite passed 74 tests; strict-response
follow-up passed 31 provider tests and six start tests, plus focused post-commit
regressions. Generated schemas, changed-file formatting/lint and relevant types
passed. Independent review accepted spec compliance and quality after both fixes.
A premature full check was cancelled; it is not counted as a full-suite pass.
Remaining task and required-check results will be recorded as they complete. No live
mutation or completed migration is established by mocked adapter responses.

Read-only local migration preparation inventoried 15 retained work records, 11
with tracker references. The ignored `.ai-dlc/local/github-adoption-inventory.json`
records unknown remote status and unverified destinations; it is not an executable
migration plan or a complete active/planned Linear backlog inventory.

Task 2 is implemented in `603c374`. The final focused provider, workflow,
conformance and GitHub Projects suites passed 127 tests, including 38 Projects
cases. Changed-code formatting, lint, types and generated checks passed.
Independent review accepted spec compliance and quality with no actionable
findings. Evidence uses wire-level fixtures; live GitHub Projects is still
unqualified. Tests cover identity, pagination, partial attachment/status outcomes,
cancellation, stale journals and guarded reconciliation of already completed
issues.

A read-only connector lookup for the configured retained SAN-12 issue returned
"Could not find referenced Issue." The connected workspace therefore did not
provide source-status evidence for that reference. A subsequent list scoped to the configured Linear team returned no issues.
Because that connection could not retrieve the known retained issue either,
these results do not establish that the source backlog is empty. No remote
mutation was attempted. Linear source completeness remains unverified.

Task 3 is implemented in `3991faa` with review fix `2d9b7df`; independent
review accepted spec compliance and quality after the fix. Fresh onboarding,
provision and Linear-compatibility checks passed 132 tests. Six focused scaffold
selection tests passed; changed-code format, lint, types and generated checks
passed. A broader related-file run had 439 passes and one duplicate-node fixture
failure; that fixture was corrected and covered by the fresh passing run. This
is not a full-suite pass.

During an earlier compatibility test, a reserved-name dispatch regression made
unintended read-only GitHub viewer/repository requests using ambient CLI
authentication. The guard now rejects that mismatch before transport and its
regressions pass. No remote writes or authentication changes occurred. These
incidental reads do not establish planned live setup or mutation qualification.

Task 3 review found that project-only configuration omitted inherited provider
choices and enrolled account drift. The fix uses effective runtime resolution
for dispatch, planning, binding protection and every apply check. Nine real
enrollment regressions were added; the final related suite passed 141 tests and
format/lint/types/generated checks passed. Scoped re-review marked the finding
addressed with no new actionable issues.

Task 4 is implemented in `437a7d7`; independent review passed spec compliance
and approved quality with one minor historical-provenance observation carried
into whole-branch review. The focused
migration/rebind/configuration/workflow/CLI suite passed 191 tests, including
52 migration cases. Changed-code format/lint/types and generated checks passed.
Recovery fixtures include partial writes, late pathname replacement during
rollback, enrollment drift, malformed evidence and completed history copied to
another checkout. The local transaction uses inode-bound in-place writes with
durable before/after evidence; this is bounded recovery, not crash-atomic
multi-file replacement. Readers may observe intermediate content.

## Required verification before final review fixes

On clean commit `685a0f8e9cdc4ad9edf68f70264cd4a6cbd6077a`, the prepared
`ai-dlc project check --required` passed all five required outcomes: generated,
format, lint, types and test. The full suite passed **1,106 tests** in 280.39
seconds. The local receipt at `.ai-dlc/local/github-ticket-required-1.json`
records the exact revision and `dirty=false`; this is local candidate evidence,
not merged-revision CI. `openspec validate --all --strict` passed all 14 items.
These pre-fix results are retained as historical evidence. Later documentation-only
evidence updates do not change which code revision these results qualify.

## Final review fixes

The whole-branch review required two adapter identity corrections: GitHub reads
did not verify a configured viewer, and Linear reads did not verify a configured
team. Commit `d2c3807` adds those checks behind the adapter boundary, preserving
legacy behavior when the identities are absent. Seventeen new real-adapter
transport-fixture cases include wrong identity at preview, drift at apply, and
already-closed GitHub finish. TDD reproduced 13 missing-guard failures first.
The final affected suite passed 304 tests without skips; format/lint/types and
generated checks passed. Scoped re-review accepted both P2 fixes and the P3
documentation response, with no new actionable findings.

The review's minor historical receipt observation is now explicit in the
migration runbook: subsequent-migration guards protect unresolved outcomes, not
the integrity of every completed historical prepared receipt. Clone-safe
historical integrity hardening remains deferred.

## Final local qualification

The corrected code and finalized behavior specification were verified on clean
commit `0f43575a92f0bbad96908749a1f8019bf5a8e650`. All five required outcomes
passed: generated, format, lint, types and test. The full suite passed **1,123
tests** in 264.29 seconds, with no skips. Receipt
`.ai-dlc/local/github-ticket-required-2.json` records that exact revision and
`dirty=false`. All 14 OpenSpec items passed strict validation again.

Whole-branch review covered `9b6ca29..685a0f8`; scoped re-review covered
`685a0f8..0f43575`, including the identity fixes and clarified requirement.
No Critical/Important findings remain. Historical completed-receipt integrity
hardening is explicitly deferred, with its current boundary documented. The final
commit after these checks only records qualification, task status and handoff;
it does not add runtime changes or establish merged-revision CI.

## Delivery and activation boundary

Implemented: capability-based work start, GitHub Issues with optional Projects v2,
named guided setup, and provider-neutral default-only/selected migration to
verified existing target tickets. Existing all-work rebind remains available.

Still needed before live adoption:

- Select the destination repository and Project, and sign in locally with suitable
  Projects access; the inspected CLI credential lacked `read:project`.
- Obtain the correct Linear source access or an export of active/planned work.
  The current connector could not retrieve a known retained issue and returned an
  empty team-scoped list; that is not evidence of an empty backlog.
- Review exact target mappings and any ticket-creation intent. The new migration
  command maps existing targets; automatic remote creation/import remains a
  separate parent task. Local records alone omit remote-only backlog/history.
- Qualify the chosen GitHub repository/Project through designated disposable live
  operations, including partial-write recovery. Fixtures and health reads do not
  prove this behavior against the live service.

Plane and Jira adapters and broader parent onboarding remain subsequent work.
Plane installation is unnecessary for GitHub. Confluence integration is deferred
until the existing custom server can be reviewed; Obsidian stays local. The
separate SAN-12 cleanup branch/blocker is not resolved or integrated by this work.

No real tracker selection, retained-work mapping, issue state, or authentication
was changed. No archive, PR, merge, package publication, or work finish was
attempted. The child remains active for its live and integration gates.
