# Run the declared skill evaluation once with controls and archive the results

## Why
`agents/evaluation.toml` declares a release evaluation (`status = "pending"`, model
`gpt-5.6-sol`, five repetitions, controls required, human review required) and
`agents/evaluation-scenarios.json` lists eight scenarios whose `baseline` and
`with_skill` fields are `not-run`. Nothing in the repository can execute that
declaration: no module calls a model API, and every "skill quality" claim in the
documentation is explicitly unmeasured. A tool that gates delivery on evidence
should be able to produce evidence about its own guidance.

## What Changes
- A runner SHALL read the declaration and the scenarios, build one control prompt
  (no skill text) and one treatment prompt (skill text supplied) per scenario and
  repetition, and call the declared model with the declared `reasoning_effort` and
  `max_output_tokens`, stopping before any call that could exceed
  `max_total_tokens` across the run.
- Every transcript SHALL be stored verbatim as JSON under
  `agents/evaluations/runs/<UTC date>-<model>/<skill>/<index>-<control|skill>-<rep>.json`
  with a `summary.json` carrying token usage and each scenario's `expected` line,
  and a `review-sheet.md` with one row per transcript for a human to mark.
- The runner SHALL NOT score, and SHALL be unable to write any pass/fail field.
- `--dry-run` SHALL print every prompt pair and the total budget without
  constructing a network client or reading a credential.
- The declaration gains `api_url` and `credential_env`; the credential is read
  only from the named environment variable, never from a file.

## Capabilities
### New Capabilities
- skill-evaluation: Controlled, verbatim, budget-bounded skill evaluation runs
  whose scoring stays with a human.

## Impact
`agents/evaluation.toml`, a new `scripts/run_skill_evaluation.py`, a new
`src/ai_dlc/harness/skill_evaluation.py`, tests, `docs/verification/skill-evaluation.md`,
the catalog and the release verification outstanding list. No CLI or MCP command
changes, no provider adapter changes, and no automatic scoring enters any check.
The live run itself needs a credential this delivery does not have; the runner,
its dry-run evidence and the documentation are delivered and the live run is
recorded as outstanding.
