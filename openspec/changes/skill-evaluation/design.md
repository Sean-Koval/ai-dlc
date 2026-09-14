# Run the declared skill evaluation once with controls and archive the results

## Context
The declaration already fixes the model, effort, repetitions and budgets, and it
requires controls and human review. Neither the `openai` nor the `anthropic` SDK
is installed and no module calls a model. `httpx` is an existing dependency, so
the runner talks to an OpenAI-compatible chat-completions endpoint through it.
No credential is available in the delivering environment, so the live run cannot
be performed here and must not be simulated.

## Goals / Non-Goals
Execute the declared protocol exactly once, verbatim and within budget, and hand
the transcripts to a human. Do not choose a different model, change the
scenarios, score automatically or feed scores into checks. Do not read tokens
from files or record them anywhere.

## Decisions
- Provider-neutral transport. `api_url` names the full OpenAI-compatible
  chat-completions endpoint; `credential_env` names the environment variable
  holding the bearer token. The runner reads only `os.environ[credential_env]`
  and refuses to start a live run without it. `reasoning_effort` and
  `max_output_tokens` map to `reasoning_effort` and `max_completion_tokens`.
- Injected client. The package function `run` takes a client object with one
  `complete` method; the script builds the `httpx` client only on the live path.
  Tests exercise the dry-run path with a fake client and assert that no socket
  or HTTP client is constructed. The dry-run path never touches the credential.
- Control and treatment. The control request carries the scenario prompt as the
  only user message. The treatment request prepends the skill's `SKILL.md` text
  as a system message before the same user message. Each scenario yields
  `repetitions` control and `repetitions` treatment requests, ordered control
  first per scenario so a budget stop never leaves a skill with treatment but no
  control.
- Hard budget stop. Before each call the runner adds the declared
  `max_output_tokens` to the tokens used so far; if the sum exceeds
  `max_total_tokens` the run stops and `summary.json` records the stop reason and
  the requests that were not sent. Usage is taken from the provider's `usage`
  object after each call.
- Verbatim, unscored records. A transcript holds the request, the full response
  body as returned, the usage and timestamps. The writer has a fixed field set
  and no scoring field exists in any record; `review-sheet.md` has an empty
  result column for the human. The runner never edits `evaluation.toml`; the
  maintainer sets `status = "run-pending-review"` after real transcripts exist.
- Reusable logic lives in `src/ai_dlc/harness/skill_evaluation.py`; the script
  stays thin, as with `scripts/qualify_framework.py`.

## Risks / Trade-offs
`agents/` is packaged into the wheel, so a committed run directory ships with
the engine; the run is small (eighty transcripts) and the maintainer can move it
under `docs/archive/` after review. Usage accounting relies on the provider's
`usage` object; a response without one counts the declared `max_output_tokens`
so the budget errs on the conservative side.

## Migration Plan
No records change. The two new declaration fields are additive; the dry run
works without a credential, and a live run needs only the named variable.
