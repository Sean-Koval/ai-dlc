# Design PM evaluation preparation

Status: **local preparation only; human-grounded evaluation remains pending**.

The subsequent [constructed stimulus manifest](../../agents/evaluations/design-pm/stimuli/manifest.json)
and [browser construction checks](../../agents/evaluations/design-pm/stimuli/README.md)
now supply six local inputs, including three real static captures. They are
deliberately authored inputs, not experiment outputs or human ratings. The initial
preparation evidence below describes frozen revision 995a39b; construction follow-up
is recorded at the end.

## Initial preparation at 995a39b
Six original synthetic case specifications and a proposed three-condition protocol
are prepared. No UI seeds, captures, experiment calls, human labels, preferences,
approved resource limits or quality measurements are supplied by this change.

- [Case specifications](../../agents/evaluations/design-pm/cases.json)
- [Protocol and future record templates](../../agents/evaluations/design-pm/protocol.md)
- [Scoped plan](../archive/planning/2026-09-05-design-pm-calibration.md)
- [Predecessor contract](../../openspec/specs/design-pm/spec.md)

## Prepared scope

DC01–DC04 cover bicycle repair booking, a community repair queue, municipal
collection reminders and a static museum audio guide. DH01–DH02 reserve parcel
pickup and irrigation scheduling for held-out evaluation. The set exercises the
required polished-but-broken, plain-but-usable, brand-constrained, inaccessible
and screenshot-only distinctions, plus candidate lineage/iteration limits.
These are distinct from the published library-room teaching cases.

Each case separates participant task/requirements/fixtures/access constraints from
private stimulus-construction recipes and model-authored evaluation proposals.
Case, requirement and criterion IDs are linked. Proposed score anchors and outcomes
are not human labels. `human_labels`, actual candidate manifests and observations
remain null. The corpus author has seen every case; only future fresh experimental
sessions can meet the held-out exposure boundary.

The protocol defines fixed asset/model/harness identities, actual stimulus hashes,
three matched conditions, proposed repeated/counterbalanced order, blinded human
presentation, dedicated budget approval, per-call transcripts/time/usage and
candidate-specific evidence. Independent evaluation consumes part of a matched
total resource ceiling; it is not free extra compute. An optional constructed
revision-pair probe remains separately registered and excluded from generated
outcome metrics. No runner, new service, production CLI or skill change is added.

## Verification evidence

Source bootstrap succeeded in a task-owned bootstrap home, reusing the existing
verified prerequisite downloads without replacing a shared runtime. The existing
product-delivery preparation tests passed before the new corpus was authored.
The new format/reference and packet-boundary tests first failed because the corpus
was missing: **2 failed, 2 passed**. After authoring the corpus, the same focused
command passed **4 tests in 0.03 seconds**.

The tests validate ID/partition integrity, criterion-to-requirement links,
explicit pending evidence, and the calibration participant projection excluding
held-out inputs, construction recipes and evaluator proposals. They do not build
interfaces, enforce actual harness isolation, assess proposed judgments or measure
design quality. Fresh final focused verification passed **4 tests in 0.04 seconds** after
formatting. Repository-wide formatting passed (102 files), lint passed, and type
validation reported zero errors, warnings or information messages. Managed source
render reported clean with no changes, and the generated asset checker passed.
Both embedded registration/attempt JSON templates parse and retain not-approved
and not-started status. `git diff --check` passed.

The first generated-check invocation scoped PATH only to the first command; its
second command used an unprepared Python and failed with `ModuleNotFoundError:
ai_dlc`. Repeating the configured generated check with exported prepared PATH and
`uv run --locked --no-sync` passed. This was a verification environment error,
not a skipped source failure; no source change was made to hide it.

Commands used from the source-bootstrapped checkout:

- `python -m pytest -q tests/test_design_pm_evaluation.py tests/test_product_delivery_evaluation.py`
- `ruff format --check src tests scripts`
- `ruff check src tests scripts`
- `pyright --pythonpath .venv/bin/python`
- `ai-dlc agents render --check && uv run --locked --no-sync python scripts/check_generated.py`

Whole-suite and integrated required checks are coordinator-owned for this batch;
no whole-suite success is claimed by the focused result.

## Remaining work and qualification

| Criterion | Prepared | Still required |
| --- | --- | --- |
| DE-01 | Six original case specifications, proposed observations/anchors, 4/2 partition and exposure rules | Build and hash actual stimuli/captures; obtain human labels/anchors; approve freeze before tuning |
| DE-02 | Three-condition protocol, proposed ordering, resource accounting and exact future records | Approve concrete models/harness/conditions and dedicated limits; execute matched attempts; preserve actual evidence and human comparisons |
| DE-03 | Null human labels, unavailable evidence and explicit report limitations | Obtain human judgments, report negative results/disagreement and make an evidence-based workflow recommendation |

Actual fixture construction is additional local work, not an unavailable human
input; it has not been silently counted as delivered by these case specifications.
Human taste/defect labels, participation consent and dedicated budget approval
require the designated people. Protocol choices remain proposals until approved.
`agents/evaluation.toml` is a separate pending release evaluation and its budget is
unchanged. Issue #16 stays open; normal independent review, integrated checks and
merged-revision delivery evidence remain required, and cannot substitute for the
actual human-grounded experiment.

## Constructed stimulus follow-up

Six original local HTML inputs now exist, with three 390×844 rendered PNGs for
DC04 and an original synthetic council kit for DC03. A separate DH02 later
revision supplies the optional constructed regression probe. Artifact hashes,
participant allowlists and structured observed results are in the stimulus
manifest/observations; coordinator instructions explain isolated serving/reset
and prohibit private notes, held-out material or DC04 source in participant packets.
The corpus itself retains the original specification snapshot and null human
labels. No experiment registration, spending approval or human rating is implied.

Installed Node 22.23.1, cached Playwright CLI 0.1.18 and installed Chrome
152.0.7977.82 exercised the fixtures locally without downloading a browser/runtime.
The checks reproduced the date-persistence, keyboard-dismissal and constructed
cross-zone regression failures, and checked queue idempotency/address persistence.
All three museum captures were visually inspected; playback remains unverified.
These observations establish only that the deliberate inputs behave as recorded.
No model condition or human design-quality comparison was run.

A new integrity/access test first failed on the absent stimulus manifest; after
construction, the five combined preparation tests passed. It checks actual hashes,
case coverage, participant exclusions and PNG dimensions. Full integrated required
checks remain coordinator-owned; current focused/static results are recorded in
the child handoff. Human review of stimuli/anchors and approved execution limits
remain pending before any actual comparison or held-out release.

Final child verification: **5 focused tests passed in 0.04 seconds**; repository
formatting passed for 103 files; lint passed; type validation reported zero errors,
warnings or information messages. Managed source render and generated-asset checks
passed, as did whitespace checks. Browser and loopback server were closed after
capture/checks. Integrated whole-suite verification remains pending with the coordinator.
