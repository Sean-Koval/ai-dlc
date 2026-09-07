# GitHub ticket workflow qualification

Implementation branch: `codex/github-ticket-workflows`, based on planning commit
`0775b90`. Live and fixture evidence are recorded separately.

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
provide source-status evidence for that reference. No broader workspace inventory
or remote mutation was attempted from that result. Linear source completeness
remains unverified.

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
