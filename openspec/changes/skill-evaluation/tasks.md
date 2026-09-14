# Run the declared skill evaluation once with controls and archive the results

## Implementation
- [ ] 1.1 Add `api_url` and `credential_env` to `agents/evaluation.toml` and a declaration loader that reads the credential only from the named environment variable.
- [ ] 1.2 Build control and treatment prompt pairs per scenario and repetition, with regression tests for ordering and skill text.
- [ ] 1.3 Run an injected client within the hard `max_total_tokens` stop, writing verbatim transcripts, `summary.json` and `review-sheet.md` with no pass/fail field, with regression tests.
- [ ] 1.4 Add `scripts/run_skill_evaluation.py` with `--dry-run`, proven in tests to make no network call with `PATH=""` and the credential unset.
- [ ] 2.1 Record the runner, the dry-run evidence and the outstanding live run in `docs/verification/skill-evaluation.md`, enrol it in the catalog and link it from release verification.

## Verification and delivery
- [ ] 9.1 Record documentation-impact dispositions for the change.
- [ ] 9.2 Validate this OpenSpec change and run required project checks.
- [ ] 9.3 Update from the target branch, review the pull request, merge with fresh checks and verify merged-revision CI receipts.

## Live run
- [ ] 3.1 With the named credential set, run the evaluation once, commit the transcripts under `agents/evaluations/runs/`, set `status = "run-pending-review"` and record the run in the verification document.
