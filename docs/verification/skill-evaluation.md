# Skill evaluation verification

## Declared protocol and current evidence

The declaration in [`agents/evaluation.toml`](../../agents/evaluation.toml) remains
`status = "pending"`. The September 14, 2026 delivery verified the runner and its
dry run; no live model transcripts or human scores were produced. `OPENAI_API_KEY`
was unavailable in the delivering environment. The live run and human review
remain outstanding release evidence.

The unchanged protocol declares `gpt-5.6-sol`, reasoning effort `high`, five
repetitions per condition, at most 2,000 output tokens per request, and a 200,000
total input-plus-output token budget. Eight scenarios yield 40 no-skill controls
and 40 skill treatments. Each scenario sends all controls before its treatments.
The treatment prepends the shipped skill text to the same scenario prompt.

The dry run completed with an empty `PATH` and no credential:

```sh
PATH='' .venv/bin/python scripts/run_skill_evaluation.py --dry-run
```

It printed all 80 requests, their expected behavior, and the declared budget,
without constructing a network client. Regression tests prohibit client creation
and credential reads on this path, exercise the script in a subprocess with an
empty `PATH`, and cover budget stops, verbatim response preservation, usage
failures, control/treatment accounting, and refusal to overwrite run evidence.
Synthetic responses stay in temporary test directories and are not live evidence.
The ordinary command without a credential refused before constructing a client
or creating a run directory.

## Running and reviewing the live evaluation

Make the named credential available only through the process environment, then:

```sh
python scripts/run_skill_evaluation.py
```

The default destination is
`agents/evaluations/runs/<UTC-date>-<model>/<skill>/<scenario-index>-<control|skill>-<rep>.json`.
Each record includes the exact request, untouched response JSON text, usage when
available, timestamps, and expected behavior. `summary.json` lists every scenario,
confirmed token usage, any reserved allowance for uncertain usage, the stop
reason, and unsent request paths. `review-sheet.md` contains a blank human result
and notes column per transcript. The runner never writes grading fields or changes
the declaration/scenario statuses. Provider response text is preserved even when
it contains model-generated judgments; those are not runner-assigned scores.

Existing run directories are refused before constructing a client. Use a new,
explicit `--out` directory for a separately authorized repeat; never remove or
overwrite earlier raw evidence to make a run look complete. A transport failure
stops without retrying an uncertain charged request. An interrupted run may retain
only the transcripts written before interruption and remains incomplete evidence.

Before each model request, the OpenAI adapter counts that exact model/input through
[`POST /responses/input_tokens`](https://developers.openai.com/api/reference/typescript/resources/responses/subresources/input_tokens/methods/count).
It reserves the counted input plus the full declared output allowance against the
remaining total. It stops rather than reducing the declared per-request budget.
The [Responses output limit](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)
includes visible output and reasoning tokens. Missing counts prevent generation;
missing or inconsistent response usage stops subsequent requests and retains the
raw response. A provider violation of its counted allowance is reported explicitly,
with any valid actual usage recorded. No client-side guard can undo a provider
that violates its advertised count or output limit.

After real transcripts exist, the maintainer may set
`status = "run-pending-review"` and record the actual model/date, confirmed usage,
run path, completion or partial-run limits, and outstanding human scoring here.
A human then reviews every transcript against its expected behavior. Neither
passing fixtures nor a populated run directory establishes skill quality or
satisfies the human-review gate.
