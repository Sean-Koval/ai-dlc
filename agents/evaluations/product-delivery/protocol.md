# Product-to-delivery calibration protocol

Status: **prepared; not approved for execution**. No comparisons, paid runs or
human labeling have been performed under this protocol. The model-authored
expected decisions in `cases.json` are proposals for review, not ground truth.
This small experiment does not replace `agents/evaluation.toml` or satisfy its
pending release gate. It evaluates harness guidance, not an autonomous product
manager or a provider-specific development process.

## Scope and preparation

The six newly authored synthetic cases cover ambiguous new product demand,
contradictory requirements, a compatible legacy increment, a mechanical correction,
an unvalidated feature request and a risky migration. Each partition includes
both greenfield and brownfield work. `C01`–`C04` are calibration cases; `H01` and
`H02` are held out from prompt tuning. Evidence is supplied fictional case context,
including fictional stakeholder approvals; those approvals are not evaluation
labels or authorization to act on any real system.

Case metadata names predecessor requirements PS-01 through PS-03 and applicable
TR-01 through TR-03. Requirement IDs, material unknowns, disallowed assumptions and
expected decisions are evaluator notes. Participants receive only `id`, `mode`,
`prompt` and `evidence`, plus the frozen condition's approved guidance assets.

The author has seen every case. This is an experimental exposure boundary for
fresh future sessions, not a claim that the dataset is secret, that the author is
blind, or that a model has never encountered similar problems. Neither the full
repository nor `cases.json` may be attached to a tuning or participant session.
A coordinator who can access the corpus creates the allowed input packet. No
runtime isolation tool or automatic runner is supplied by this preparation.

## Calibration-only input boundary

A coordinator can produce the calibration projection with this transparent local
expression, then inspect the resulting packet before use:

```python
calibration = [
    {key: case[key] for key in data["participant_fields"]}
    for case in data["cases"]
    if case["held_out"] is False
]
```

`participant_fields` is exactly `id`, `mode`, `prompt`, `evidence` and the resulting
IDs must be exactly C01–C04. Do not include evaluator notes, proposed decisions,
human labels, this scoring protocol or any held-out case content. Supply one case
per fresh session. Preparation tests validate this projection and corpus identity;
they do not enforce real harness isolation or demonstrate decision quality.

The four calibration cases may inform revisions only after the human/budget plan
is approved. Freeze all condition prompts, assets, model/harness settings, scoring
rules and approved resource limits before releasing held-out inputs to fresh
sessions. Record exact byte hashes and the freeze revision/time. A coordinator
must attest to packet contents and session exposure. If a held-out case or its
outputs informed tuning, record contamination, exclude it from confirmatory
held-out reporting, and do not silently relabel it or replace it after seeing a
result. Any replacement requires a separately versioned, predeclared experiment.

## Registration before any execution

The following are proposed choices, not authorization: paired baseline/candidate
conditions, two repetitions per case, and equal declared limits for each matched
pair. Model identity, harness, actual limits, spending cap and human participation
are deliberately unset. Do not borrow approval from the separate release evaluation
or from earlier synthetic skill checks. An identified human must approve the
completed registration and dedicated budget before any experimental run.

Use an immutable registration with these fields, retaining null for anything not
yet known. Null is unavailable or pending, never zero cost, zero usage or approval.

```json
{
  "experiment_id": null,
  "status": "not_approved",
  "protocol_revision": null,
  "protocol_sha256": null,
  "corpus_revision": null,
  "corpus_sha256": null,
  "participant_packet_schema_version": null,
  "condition_A": {"meaning": "baseline", "asset_manifest": null, "prompt_path": null, "prompt_sha256": null},
  "condition_B": {"meaning": "candidate", "asset_manifest": null, "prompt_path": null, "prompt_sha256": null},
  "model": {"provider": null, "id": null, "snapshot_or_version": null, "reasoning_effort": null, "sampling_settings": null},
  "harness": {"name": null, "version": null, "configuration_sha256": null, "system_prompt_sha256": null, "tools_and_permissions": null, "environment_version": null},
  "budget": {"approval_status": "pending", "approved_by": null, "approved_at": null, "approval_reference": null, "currency": null, "total_spend_cap": null, "per_run_input_tokens": null, "per_run_output_tokens": null, "per_run_total_tokens": null, "per_run_wall_seconds": null, "total_token_cap": null},
  "design": {"status": "proposal", "repetitions_per_case": 2, "calibration_ids": ["C01", "C02", "C03", "C04"], "held_out_ids": ["H01", "H02"], "execution_schedule": null, "scorer_order_seed": null},
  "human_plan": {"approval_status": "pending", "labelers": null, "raters": null, "adjudicator": null, "rating_budget": null, "approval_reference": null},
  "freeze": {"status": "pending", "revision": null, "at": null, "condition_hashes": null, "human_label_artifact_sha256": null, "approved_by": null},
  "missing_evidence": ["approved conditions, model, harness, dedicated budget, human participation, labels and freeze record"]
}
```

Each asset-manifest entry must retain the exact repository revision or upstream
version, relative path, raw byte SHA-256, role in the packet and whether referenced
supporting assets are included. The baseline must be an explicitly reviewed earlier
guidance set; never use an empty control or choose a favorable baseline after seeing
outputs. The candidate must be an exact reviewed revision. Compare matched input
packets and the same approved supporting context. The intended treatment is the
guidance asset set; document every other difference and exclude unmatched runs from
paired claims. If the harness cannot supply an immutable model snapshot, preserve
the exact reported model identity/version and disclose that reproducibility limit.

## Proposed order and execution controls

Before execution, materialize the full schedule in the approved registration. For
case index `i` in each partition's listed order and repetition `r` starting at zero,
use A→B when `(i + r)` is even and B→A otherwise. Thus each case appears once in
each condition order over the proposed two repetitions, and each partition is
balanced. Two repetitions would mean 16 calibration responses and 8 held-out
responses; these are proposed counts, not approved spending or completed runs.

Every condition/case/repetition starts a new isolated context. Do not reuse chat
history, run output, hidden evaluator notes, repository access, network tools or
another condition's response. The operator checks the actual packet and permission
configuration, not just the model's assurance that it ignored material. Preserve
exact input and output, tool messages, errors, refusals, truncation and interruptions.
A timeout or budget exhaustion is an observed outcome, not a reason to secretly
increase one condition's budget. Record any rerun and its predeclared reason; keep
the original result and account for all spend. Stop when the approved total limit
is reached. A changed model, harness, prompt or budget starts a new registered block.

Randomize or counterbalance the *human presentation order* separately, using the
recorded seed and opaque run labels. Hide condition names, proposed decisions and
other condition outputs from the initial independent judgment. Do not hide material
failures or truncation from reviewers. Record a blinding failure if the output
reveals its condition or a rater recognizes the case/author.

## Exact future run record

Create a separate record for every attempted response, including failed attempts.
No such record exists yet. Preserve raw transcripts and usage responses alongside
this structure; redaction requires an audit note and a protected original.

```json
{
  "run_id": null,
  "experiment_id": null,
  "case_id": null,
  "partition": null,
  "repetition": null,
  "condition": null,
  "execution_order_index": null,
  "pair_id": null,
  "registration_sha256": null,
  "case_input_path": null,
  "case_input_sha256": null,
  "condition_prompt_path": null,
  "condition_prompt_sha256": null,
  "asset_manifest": null,
  "model": {"provider": null, "id": null, "snapshot_or_version": null, "reasoning_effort": null, "sampling_settings": null},
  "harness": {"name": null, "version": null, "configuration_sha256": null, "system_prompt_sha256": null, "tools_and_permissions": null, "environment_version": null, "session_id": null},
  "budget": {"approval_reference": null, "input_token_limit": null, "output_token_limit": null, "total_token_limit": null, "wall_seconds_limit": null, "spend_cap": null, "currency": null},
  "time": {"started_at_utc": null, "finished_at_utc": null, "wall_seconds": null, "measurement_source": null},
  "usage": {"input_tokens": null, "output_tokens": null, "reasoning_tokens": null, "cached_input_tokens": null, "total_tokens": null, "provider_report_path": null, "actual_cost": null, "currency": null, "cost_source": null, "estimated_cost": null, "estimate_basis": null},
  "transcript": {"path": null, "sha256": null, "input_included": null, "tool_messages_included": null, "complete": null, "redactions": null},
  "outcome": {"status": "not_started", "finish_reason": null, "truncated": null, "error": null, "rerun_of": null, "rerun_reason": null},
  "exposure": {"fresh_session_verified_by": null, "packet_verified_by": null, "prior_case_or_output_exposure": null, "holdout_contaminated": null},
  "human_judgments": null,
  "missing_evidence": null
}
```

Do not sum overlapping token categories without the provider's accounting rules.
Keep billed/actual cost separate from any estimate; unavailable cost remains null.
Record the full approval limits even if the harness enforces only a subset, and
flag unenforceable limits before execution. Never treat `not_started` as a run.

## Human labels and decision metrics

Before viewing model proposals or outputs, designated humans label the allowed
participant inputs. A label records labeler identity/role, timestamp, case/input
hash, acceptable next-action routes, required observations, prohibited assumptions,
required behavior-to-verification links, rationale and uncertainty. More than one
route can be acceptable when justified. Store independent labels and disagreements
before adjudication; never silently overwrite them with the model-authored proposal.
Keep the prepared corpus immutable and store later labels in a separate hashed
artifact referenced by the freeze record. If no human label exists, report decision
accuracy as **pending**, not a comparison against `expected_decisions`.

Designated humans independently rate blinded outputs with transcript line/span
references. Human judgments record rater identity/role, time, blinding status,
observed route, accepted-route match, required-observation hits/misses, unsupported
claim spans, unjustified scope additions, missing behavior/verification links,
usefulness score, rationale, confidence and unresolved disagreement. Prefer a second
independent labeler/rater and a separately named adjudicator; their actual identities,
availability and rating budget remain subject to human-plan approval. If only one
participates, retain that limitation rather than inventing agreement.

Report these metrics per case, condition and partition, with actual denominators:

| Metric | Human-grounded definition |
| --- | --- |
| Decision accuracy | Number of rated responses whose next action is in the frozen human-accepted routes, divided by responses with a human label and completed route judgment. Preserve rationale; do not label undecidable cases wrong or correct automatically. |
| Missing decision observations | Human-required observations absent from the output, with cited spans or absence notes. Report required-observation denominator and case counts. |
| Invented facts | Count and cite unsupported statements presented as fact. Proposed hypotheses explicitly labeled as such are not automatically inventions. |
| Unjustified scope growth | Count additions requiring product authorization or behavior beyond the input that are presented as committed work rather than optional proposals. Cite each addition and its human judgment. |
| Missing behavior/verification links | Count missing links against the human-frozen required link set. Mark nonapplicable mechanical/no-spec cases N/A, not zero defects demonstrating superiority. |
| Human usefulness | Ordinal 1–5 with rationale: 1 unusable or misleading; 2 major revision; 3 usable with substantive revision; 4 usable with minor clarification; 5 directly useful within the supplied scope. Do not equate a high score with live product value. |
| Resource and failure outcomes | Actual time/usage/cost where available, truncation, refusal, error and missing-evidence counts. Keep failed attempts visible alongside decision metrics. |

Compare paired outcomes, including ties, negative results and disagreements. Show
case-level data and separate calibration from held-out observations. State how many
unique cases, responses and humans contributed; repetitions are not new independent
products. With this small synthetic corpus, descriptive results cannot establish
universal quality improvement, production value, live integration readiness or an
unqualified causal claim. Any unblinded or contaminated observations remain clearly
separate. No scores, ratings, successful runs or improvement are claimed today.
