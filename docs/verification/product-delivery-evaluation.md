# Product-delivery evaluation preparation

Status: **local preparation only; evaluation pending**. Six newly authored
synthetic cases and a proposed controlled-comparison protocol are available.
There are no human labels, approved experimental budget, model/harness selection,
experimental transcripts, scores or improvement findings from this work.

- [Protocol](../../agents/evaluations/product-delivery/protocol.md)
- [Case corpus](../../agents/evaluations/product-delivery/cases.json)
- [Scoped plan steering](../superpowers/plans/2026-09-05-workflow-quality-calibration.md)

## Delivered preparation

The four calibration cases cover an ambiguous greenfield product, contradictory
greenfield requirements, a legacy compatibility increment and a mechanical
brownfield correction. Two held-out cases cover an unvalidated greenfield feature
request and a risky brownfield migration. Evidence, material unknowns and
unsupported assumptions are separate. Each expected decision is explicitly a
model-authored proposal; `human_labels` is null and its status remains pending.
Fictional stakeholder approvals inside a case are supplied context, not human
evaluation labels or authorization to affect any real system.

The protocol proposes two matched repetitions with balanced A/B order, subject to
later approval. Exact condition assets, model, harness/version, settings, budget,
transcripts, timing, usage, cost provenance and human judgments have defined future
record fields. Their unavailable values remain null. Human labels must precede
scoring, and the model-authored proposals cannot substitute for them. Independent
ratings, disagreements, failures and missing evidence remain visible.

Held-out status is an experimental session boundary: the author has seen all six
cases. Calibration packets contain only four cases and participant-visible fields.
Future sessions must be fresh and receive inspected packets without repository
access, scoring notes or held-out content before freeze. A projection check cannot
prove future harness isolation or prevent a coordinator from exposing the full file.

## Local verification scope

Two preparation invariants initially failed because the corpus did not exist,
then passed after authoring. They validate six unique identities, the four/two
partition with both entry modes in each, synthetic evidence, pending human labels,
proposal status, and the documented calibration projection excluding held-out
inputs and evaluator keys. These tests do not assess correctness of proposed
product decisions, establish human agreement, or demonstrate model improvement.
No runner, production service, CLI or skill was added or changed.

Source is based on accepted dependency candidate `4058b24`. Root coordinates its
integration with the current roadmap and archive state. This record does not
substitute for the separate pending `agents/evaluation.toml` release experiment.

## Pending evidence and next authorized boundary

| Criterion | Prepared | Still pending |
| --- | --- | --- |
| EV-01 | Six original synthetic cases and model-proposed decision observations | Human labels, independent review and approved frozen label artifact |
| EV-02 | Version/budget/transcript/usage schema, proposed balancing and held-out protocol | Approved registration and spending limit, exact conditions/model/harness, freeze and actual comparisons |
| EV-03 | Explicit null labels, human scoring definitions and limitations | Human judgments, disagreements, usefulness ratings and evidence-based reporting |

The next experimental step requires an identified human's approved model/harness,
dedicated budget and participation plan. No execution is authorized by this local
preparation. Independent source review, dependency integration and exact merged
revision checks remain root-owned delivery steps. The evaluation ticket remains
incomplete until its actual human-grounded comparison and delivery evidence exist.

The first focused run passed 313 tests and failed the package-build check. A direct
reproduction reported `No space left on device` while extracting the inherited
tracked Rust build artifacts from the source distribution; this was an environment
failure, not evidence that the cases or protocol passed packaging. The failed
reproduction output was removed; tracked historical files were preserved. The two
preparation invariants were rerun and passed. Required verification is pending
until a complete result is recorded below.

## Complete retry after the packaging repair

The independently reviewed packaging fix `8551b09` was applied here as `bbcaf39`.
It excludes compiled `target/` outputs from Python source distributions while the
real packaging test verifies that `Cargo.toml` and historical `crates/*.rs` source
remain included. No tracked legacy source was removed and no scanner helper was
replaced by the cherry-pick.

One full required-check retry passed **all five checks and 1,212 tests** at clean
revision `bbcaf39d670538b72ad80460a6516f6ff85d8c91`. The
[receipt](product-delivery-evaluation/local-checks.json) records that exact source
revision. This evidence note and receipt were finalized afterward; the preparation
source, tests and assets were frozen throughout the passing run. Both JSON future
record templates in the protocol also parse, with their approval/budget/human
fields still pending or null. The earlier failed packaging attempt remains
recorded above rather than being relabeled successful.

No new behavioral specification is required for this verification-only
preparation. This passing local result establishes artifact and repository checks,
not human labeling, executed experimental comparisons or product-quality gains.
