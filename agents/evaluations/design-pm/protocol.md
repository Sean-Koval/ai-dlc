# Design PM comparison protocol

Status: **local preparation; not approved for execution**. Deliberately constructed
seed interfaces and static captures are now recorded in [the stimulus manifest](stimuli/manifest.json)
with [author construction checks](stimuli/README.md). They are inputs, not outputs
of any experiment condition. No experiment responses or human ratings exist. Proposed expectations are model-authored hypotheses, not ground truth.
This verifies the delivered [Design PM contract](../../../openspec/specs/design-pm/spec.md);
it does not change that contract or create a production evaluation service.
The dedicated experiment remains separate from `agents/evaluation.toml` and the
product-delivery experiment. Neither existing budget authorizes this protocol.

## Cases and evidence boundary

`cases.json` specifies six original synthetic cases in distinct products. DC01–DC04
are calibration cases; DH01–DH02 are held out. They cover polished-but-broken,
plain-but-usable, required brand reuse, static-only evidence, keyboard failure and
revision regression. The public library-room teaching examples are not held-out
cases and are not imported as experimental measurements.

The corpus preserves the original **case specification snapshot** at 995a39b.
Its private `stimulus_plan` recipe and null candidate/observation fields describe
that preparation point; the separate stimulus manifest and construction observations
record the subsequent built inputs without inventing experimental results.
Before a case can run, a coordinator must build its original seed/captures, record
source and evidence hashes, verify the intended fixture behavior independently,
and obtain human review of the task and scoring contract. Missing construction is
local work; missing human judgment cannot be filled by model assertions. Fixture
verification is not evidence that the guidance improves a generated interface.
For the screenshot-only case, actual identified captures are sufficient for the
visual condition, while interaction remains unverified.

The DH02 constructed revision-pair stress probe is optional and separately
registered. It exercises evaluation/selection of known candidate lineage; it must
not be counted as a naturally generated regression or pooled with matched
three-condition generation outcomes. Its constructed source and observed behavior are now recorded in the stimulus
manifest; experimental inclusion and separate resource allocation remain pending.

The case author has seen all cases. Fresh future participant/evaluator sessions
must not have seen held-out cases or scoring notes before freeze. This is an
experimental exposure rule, not a claim of dataset secrecy or model training
independence. Never provide full repository access, the complete corpus, this
protocol, construction recipes, proposed judgments or human answers to an
experimental participant. Construct and inspect one allowed packet per session.

For calibration inputs, use this projection and inspect its output:

```python
calibration = [
    {key: case[key] for key in data["participant_fields"]}
    for case in data["cases"]
    if case["held_out"] is False
]
```

The resulting IDs must be DC01–DC04. Only `id`, `task`, `requirements`, `fixtures`
and `access_constraints` are included, together with the separately frozen actual
seed/access manifest and the selected condition's approved assets. Human labelers
receive the same task and actual seed evidence without model proposals. Hold-out
packets may be released only after the complete protocol, assets, human scoring
rules and resource allocation have been frozen. A coordinator records packet and
session exposure. Leaked cases remain visible as contaminated development data;
exclude them from confirmatory reporting. Do not silently replace or relabel them
after seeing outputs. New cases require a new registered block.

## Three conditions and comparable resources

The conditions are proposed until an identified human approves registration:

- **A — current guidance:** the explicitly reviewed baseline asset set and its
  ordinary generation workflow. Baseline means recorded existing guidance, not
  an empty control or a retrospectively selected weak prompt.
- **B — rubric-only generation:** the same common task/seed, plus the frozen
  Design PM brief/rubric-generation guidance. The generator receives its contract
  and may perform recorded self-review; it has no independent evaluator.
- **C — rubric plus independent evaluation:** the same rubric-generation guidance
  and common task/seed, with a fresh independent evaluator receiving the brief,
  versioned contract, identified candidate and access instructions. Generator
  self-ratings are withheld. Feedback and any resulting revision are preserved.

Freeze exact prompt bytes, skill/template/example manifests and inclusion of
referenced assets for each condition. Human outcome criteria are frozen separately
from a condition's generated rubric. An easier generated rubric cannot redefine
success. Match source task, initial seed, fixtures, brand assets, allowed tools,
generator model/settings and overall resource ceilings. Declare every intended
treatment difference. The independent evaluator's model/settings are separately
recorded, even when identical to the generator's. Self-review or unavailable
independence must never be relabeled as independent evaluation.

Proposed primary comparison uses equal **total** time/token/spend ceilings per
workflow attempt, including generation, rubric construction, evaluation and
revisions. C allocates part of that ceiling to independent evaluation rather than
receiving free additional compute. Before execution, record the allocation across
stages and the maximum candidate/revision count for each condition. Numeric limits
are deliberately unset. A secondary equal-generation-budget comparison is possible
only as a separately approved block, with C's additional cost shown explicitly.
Unmatched or misallocated attempts are retained but excluded from matched claims.

Proposed repetitions: two per case, giving 24 calibration and 12 held-out workflow
attempts across the three conditions. A workflow attempt may contain multiple
model calls; 36 is not a call count or budget. Store each call and count all usage,
including failures and optional probes. These proposed counts authorize no calls.

For ordered case index `i` over DC01, DC02, DC03, DC04, DH01, DH02, choose the first
repetition's order from `[ABC, BCA, CAB][i % 3]`; reverse that order for repetition
two. Each of the six permutations occurs twice over the complete proposed corpus.
This balances overall positions, but the 4/2 partitions are not perfectly balanced
within every position. Preserve that limitation, or approve a different schedule
before freeze; do not alter order in response to outcomes. Materialize the entire
schedule with case/partition/repetition/condition and stage allocations in the
registration. Each attempt starts from a fresh isolated context and the same seed,
not the preceding condition's output.

Human presentation order is independent of execution order. Before rating, use a
recorded random seed and algorithm/version to shuffle opaque candidate labels
within matched sets. Record the exact presentation schedule, who can decode
conditions, and recognition/blinding failures. Do not conceal failed journeys,
truncation, missing captures or prior-candidate selection from human reviewers.

## Registration template

Every null is unavailable/pending, never zero spend, consent or a completed freeze.
An identified human must approve the completed registration, dedicated resource
limits and participation plan before any experimental calls. Human reviewers must
also approve the actual case stimuli and score anchors before tuning.

```json
{
  "schema": 1,
  "experiment_id": null,
  "status": "not_approved",
  "protocol": {"revision": null, "path": null, "sha256": null},
  "corpus": {"revision": null, "path": null, "sha256": null},
  "conditions": {
    "A": {"meaning": "current guidance", "prompt_path": null, "prompt_sha256": null, "asset_manifest": null},
    "B": {"meaning": "rubric-only generation", "prompt_path": null, "prompt_sha256": null, "asset_manifest": null},
    "C": {"meaning": "rubric plus independent evaluation", "prompt_path": null, "prompt_sha256": null, "asset_manifest": null}
  },
  "generator_model": {"provider": null, "id": null, "snapshot_or_version": null, "reasoning_effort": null, "sampling_settings": null},
  "evaluator_model": {"provider": null, "id": null, "snapshot_or_version": null, "reasoning_effort": null, "sampling_settings": null},
  "harness": {"name": null, "version": null, "configuration_sha256": null, "system_prompt_sha256": null, "tools_and_permissions": null, "browser_and_version": null, "environment_version": null},
  "budget": {"status": "pending", "approved_by": null, "approved_at": null, "approval_reference": null, "currency": null, "total_spend_cap": null, "total_token_cap": null, "per_attempt_input_tokens": null, "per_attempt_output_tokens": null, "per_attempt_total_tokens": null, "per_attempt_wall_seconds": null, "per_condition_stage_allocations": null, "candidate_and_revision_limits": null, "enforcement_and_unenforceable_limits": null},
  "design": {"status": "proposal", "repetitions_per_case": 2, "calibration_ids": ["DC01", "DC02", "DC03", "DC04"], "held_out_ids": ["DH01", "DH02"], "execution_schedule": null, "human_order_seed": null, "human_order_algorithm_version": null, "human_presentation_schedule": null, "optional_stress_probe_registration": null},
  "stimulus_manifests": null,
  "human_plan": {"status": "pending", "decision_owner": null, "labelers": null, "raters": null, "adjudicator": null, "rating_budget": null, "consent_and_access_limits": null, "approval_reference": null},
  "freeze": {"status": "pending", "revision": null, "at_utc": null, "approved_by": null, "condition_hashes": null, "human_label_artifact_sha256": null, "human_rubric_artifact_sha256": null},
  "missing_evidence": ["built stimuli/captures, human labels/anchors, approved conditions/model/harness/budgets, exposure attestation and freeze"]
}
```

Each asset entry records path, exact revision/upstream version, byte SHA-256, its
role in the condition and whether referenced supporting assets are included.
Each stimulus entry records case ID, source/seed revision, immutable candidate
identity, artifact hashes, reset procedure, fixture data, browser/viewport,
access instructions, permissions and independent fixture-check evidence. Do not
replace missing assets with invented URLs or synthetic observations described as
captures. If immutable model snapshots are unavailable, retain the exact reported
model identifier/version and disclose the reproducibility limit.

## Attempt, call and candidate records

Preserve a record for every attempted workflow, including refusals, interrupted
runs, timeouts and failures. `not_started` templates are not executed attempts.
Link every call, candidate and evaluation; preserve earlier candidates so later
regressions cannot erase evidence. Never add an undeclared retry to only one
condition. Log the original outcome and any predeclared retry reason and resource
use. A changed model, harness, task, prompt, rubric or limit creates a new block.

```json
{
  "schema": 1,
  "attempt_id": null,
  "experiment_id": null,
  "registration_sha256": null,
  "case_id": null,
  "partition": null,
  "condition": null,
  "repetition": null,
  "matched_set_id": null,
  "execution_order_index": null,
  "task_packet": {"path": null, "sha256": null},
  "seed_manifest_sha256": null,
  "condition_prompt_sha256": null,
  "asset_manifest": null,
  "approved_budget_and_allocation": null,
  "calls": null,
  "candidates": null,
  "selected_candidate_id": null,
  "selection_reason": null,
  "time": {"started_at_utc": null, "finished_at_utc": null, "wall_seconds": null, "measurement_source": null},
  "usage": {"input_tokens": null, "output_tokens": null, "reasoning_tokens": null, "cached_input_tokens": null, "total_tokens": null, "actual_cost": null, "currency": null, "cost_source": null, "estimated_cost": null, "estimate_basis": null},
  "outcome": {"status": "not_started", "stop_reason": null, "truncated": null, "error": null, "rerun_of": null, "rerun_reason": null},
  "exposure": {"fresh_session_verified_by": null, "packet_verified_by": null, "prior_case_or_output_exposure": null, "holdout_contaminated": null, "independence_mode": null},
  "human_judgments": null,
  "missing_evidence": null
}
```

Every entry in `calls` must include call/session ID, stage, parent attempt ID,
role, exact model/provider/version/settings, harness/version/system-prompt hash,
tools/permissions, prompt/input hashes, start/end UTC and measured elapsed time,
approved limits, raw provider usage report path/hash, available token categories,
actual billed cost or separately labeled estimate, finish reason and truncation.
Retain the complete raw transcript path/hash including inputs, tools, errors and
outputs. Preserve protected originals and an audit note for any redaction. Do not
sum overlapping token categories or infer unavailable usage from elapsed time.
Parallel call durations do not sum to workflow wall time; record both measures.

Every candidate entry must include unique candidate ID, parent ID, source revision
or artifact SHA-256, generation call IDs, task/RQ links, rubric ID/version/hash,
access instructions, fixture/reset state and available captures/traces with
hashes, viewport and browser identity. Each evaluation links reviewer/session,
independence mode, candidate ID/hash, rubric version, observed states, evidence,
criterion findings and pass/fail/unverified or anchored subjective scores.
Missing observations remain unverified. A material rubric change requires a new
version and reevaluation of candidates compared under that contract.

## Human labels, judgments and reporting

Before seeing model expectations or outputs, designated humans inspect allowed
case inputs and actual seed artifacts, label required defects and supply task-fit
and taste anchors. Store separate immutable label records: labeler identity/role,
time, task/candidate/evidence hashes, required defect IDs and reproduction,
acceptable observations, criterion anchors, rationale, uncertainty and consent
limits. Preserve individual disagreements before adjudication. Keep later labels
outside the prepared corpus and reference their hashes from registration.

Humans then independently review blinded matched candidate sets and reports.
Each judgment records rater identity/role, UTC time, opaque presentation label,
candidate and evidence hashes, rubric version, blinding/recognition status,
criterion decisions with evidence references, pairwise preference/tie/no-judgment,
reasoning, confidence and missing observations. Prefer multiple independent
raters and a named adjudicator; actual availability is pending. One rater cannot
establish agreement. A model score is never substituted for a human label.

Report actual numerators, denominators and missing counts per condition, case and
partition. Retain calibration and held-out results separately:

| Measure | Human-grounded reporting rule |
| --- | --- |
| Pairwise preference | For A/B, A/C and B/C, report wins, losses, ties and abstentions among humans with adequate matched evidence; separate taste preference from required-contract eligibility. |
| Missed required defects | Count human-labeled, observable required defects missed by the submitted report, over observable labeled defects for those candidates. No ground truth means pending, not zero. |
| False-positive findings | Count adjudicated unsupported defect findings over reviewed defect findings. Missing-access `unverified` statements are not automatically false positives. Preserve disputed findings separately. |
| Required behavior/evidence | Show pass/fail/unverified per frozen human criterion and candidate. Attractive output or an average score cannot override a required failure or missing evidence. |
| Rater disagreement | Retain independent decisions, counts and denominators before adjudication; show unresolved disagreement and rater number. Do not report agreement when ratings are absent. |
| Resource and failure outcomes | Report wall time, actual available usage/cost, estimates separately, calls, candidates, retries, refusals, truncation and missing evidence. Include failed attempts and all condition C evaluation work. |

Apply the frozen stop rules: contract satisfaction, approved budget/iteration
exhaustion, material unresolved product decision, or the approved plateau rule.
A proposed plateau is two consecutive comparable evaluations with no criterion
improvement and no required defect resolved; humans must approve it before use.
Stopping alone never implies acceptance. Preserve the best eligible earlier
candidate and its evidence; if none qualifies, report needs-work.

After real observations, recommend keeping, changing or simplifying the workflow
with case-level rationale, including negative results. Until then the recommendation
is **pending**. This small synthetic corpus cannot establish universal aesthetic
quality, production value, full accessibility compliance or client qualification.
Repetitions are not independent products. Report unsupported clients, unavailable
browser evidence, baseline differences, unblinding and contamination explicitly.
No paid/live runs, human ratings or quality improvement are claimed by preparation.
