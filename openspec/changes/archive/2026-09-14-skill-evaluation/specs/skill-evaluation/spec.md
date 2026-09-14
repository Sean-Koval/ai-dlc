## ADDED Requirements

### Requirement: EV-01 Controls and treatments recorded verbatim within budget
The skill evaluation runner SHALL read `agents/evaluation.toml` and its scenarios file, SHALL send `repetitions` control requests without skill text and `repetitions` treatment requests with the skill's `SKILL.md` text for every scenario against the declared model, `reasoning_effort` and `max_output_tokens`, SHALL stop before any request that could exceed `max_total_tokens` across the run, and SHALL store every request and response verbatim as JSON with a summary of token usage and each scenario's `expected` line.

#### Scenario: A scenario is evaluated
- **WHEN** the runner processes a scenario with `repetitions = 5`
- **THEN** it sends five control requests whose only message is the scenario prompt and five treatment requests that add the skill text, each with the declared model, effort and output limit, and writes one JSON transcript per request under `<run>/<skill>/<index>-<control|skill>-<rep>.json`

#### Scenario: The total budget would be exceeded
- **WHEN** the tokens used so far plus the counted input tokens and the declared `max_output_tokens` exceed `max_total_tokens`
- **THEN** the runner sends no further request, records the stop reason and the unsent requests in `summary.json`, and keeps every transcript already written

#### Scenario: The credential is absent
- **WHEN** a live run starts and the environment variable named by `credential_env` is unset
- **THEN** the runner refuses before constructing a client, and it never reads a token from a file

### Requirement: EV-02 No automatic pass
The runner SHALL NOT score transcripts. No runner-authored transcript, summary or review-sheet metadata SHALL contain a pass, fail or score field; verbatim provider response content SHALL remain unchanged, and the runner SHALL NOT modify `agents/evaluation.toml` or the scenarios file; a human records results in `review-sheet.md`.

#### Scenario: A run completes
- **WHEN** the runner finishes writing a run directory
- **THEN** every transcript and `summary.json` contain only request, response, usage, timing and identity fields, `review-sheet.md` has one row per transcript with an empty result column, and `status` in the declaration is unchanged

### Requirement: EV-03 Dry run makes no network call
`--dry-run` SHALL print every control and treatment prompt pair and the total declared budget and SHALL NOT construct a network client, open a socket or read the credential.

#### Scenario: Dry run without credentials or tools
- **WHEN** the script runs with `--dry-run`, an empty `PATH` and the credential variable unset
- **THEN** it exits successfully, prints every prompt pair and the budget, and no HTTP client or socket is created
