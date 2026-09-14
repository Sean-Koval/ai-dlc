# Run the declared skill evaluation once with controls and archive the results

## Implementation
- [x] 1.1 Add `api_url` and `credential_env` to `agents/evaluation.toml` and a declaration loader that reads the credential only from the named environment variable.
- [x] 1.2 Build control and treatment prompt pairs per scenario and repetition, with regression tests for ordering and skill text.
- [x] 1.3 Run an injected client within the hard `max_total_tokens` stop, writing verbatim transcripts, `summary.json` and `review-sheet.md` with no pass/fail field, with regression tests.
- [x] 1.4 Add `scripts/run_skill_evaluation.py` with `--dry-run`, proven in tests to make no network call with `PATH=""` and the credential unset.
- [x] 2.1 Record the runner, the dry-run evidence and the outstanding live run in `docs/verification/skill-evaluation.md`, enrol it in the catalog and link it from release verification.

## Verification and delivery
- [x] 9.1 Record documentation-impact dispositions for the change.
- [x] 9.2 Validate this OpenSpec change and run required project checks.
Integration follow-up: the maintainer owns fresh-base review, merge, merged-revision CI receipts, and evidence-gated work finish.

## Deferred live qualification — not delivered
The named credential is absent; this explicitly permitted delivery contains the runner and dry-run verification only. No live result or score is claimed.

3.1 With the named credential set, run the evaluation once, commit the transcripts under `agents/evaluations/runs/`, set `status = "run-pending-review"` and record the run in the verification document.
