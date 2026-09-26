## 1. Focused checks through existing manifest commands

- [x] 1.1 Add explicit shared-service selection and repeated CLI `--check ID`; reject invalid/empty/duplicate/unknown selections and selection combined with all-command mode before runtime resolution or command execution, preserving omitted-selector behavior.
- [x] 1.2 Base explicit-selection CLI success on all selected outcomes while retaining full manifest required IDs/digests in receipts; preserve existing runtime-unavailable, timeout and cancellation handling.
- [x] 1.3 Test requested order, optional IDs, omitted-selector defaults, invalid selection without execution/receipt, successful subset exit, selected failures/cancellation, and successful partial receipt rejection by the existing trusted completion validator.

## 2. Honest generated starter checks

- [x] 2.1 Change frontend command and direct Playwright test to fail actionably without `BASE_URL`, retain opt-in composition and no-install behavior, and update tests previously expecting a successful skip.
- [x] 2.2 Add Python initialization-only `application-tests`, a standard-library behavioral starter test, and a minimal runner rejecting missing/empty/all-skipped suites; retain syntax validation and authored-content preservation.
- [x] 2.3 Exercise generated Python commands offline: starter passes; syntax-valid output regression, failing test, no discovered tests and all-skipped tests fail; added tests are discovered; clean runs leave Git clean. Cover non-Python/adoption exclusions and preserved authored manifests/checks/tests.
- [x] 2.4 Verify missing frontend configuration fails before package/browser execution, configured command propagates failure and success, and a prepared real local browser smoke passes when available. Report unrun live coverage explicitly.

## 3. Documentation and delivery evidence

- [x] 3.1 Update README, portable project guidance and existing frontend workflow copies for focused edit checks, full required verification before merge, honest starter coverage and team-owned commands; review greenfield/brownfield guidance and catalog mappings.
- [x] 3.2 Validate this OpenSpec change; review affected canonical docs and record content-bound documentation-impact dispositions.
- [x] 3.3 Complete independent implementation review and prepare the integrated required-check run with recorded focused-test evidence.

Then archive the change before merge, integrate the current target and run all required project checks for the final delivery revision. Complete work through the existing exact merged-revision finish gates. Selected-check results never substitute for full required evidence; archiving is not a claim that merge or finish has happened.
