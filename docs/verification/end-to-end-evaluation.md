# End-to-end evaluation verification

`ai-dlc eval` runs the same task twice in isolated containers, once with the
engine installed (`treatment`) and once without it (`baseline`), grades both with
tests the attempt can never read, and reports the difference. It is a maintainer
tool. Its inputs live in [`evaluations/`](../../evaluations/README.md), outside
the wheel.

## Current evidence and its limit

As of September 19, 2026 the runner, grader, report and candidate-image recipe
are delivered and verified on one machine (WSL2 Ubuntu 22.04, Docker 26.1.3). The
only driver is `deterministic`: a script of fixed steps. The shipped script writes
the reference solution in the treatment arm only, so its result exercises the
machinery and **says nothing about AI-DLC's value**. Every report from it carries
`evidence_kind = "fixture"` and the claim `none`. A finding needs a real coding
client in both arms; that is issue #138 and has not been run.

Verified by real runs on that machine:

- both arms run as uid 1000 with no network, a read-only root, all capabilities
  dropped, and memory and process limits; direct egress fails and a 900 MB
  allocation under a 128 MB limit is killed;
- a timeout and a cancellation each stop the attempt, still collect the tree, and
  leave no container or volume;
- `eval image` built the candidate in 21 seconds; the engine reported
  `ai-dlc 0.4.0` with networking off and was absent from the baseline image;
- a forged grading file, a truncated, malformed or missing event trace, a missing
  attempt directory, a leaked credential value and a failed cleanup each produce
  `incomplete`, `unavailable` or `cleanup_clean = false`, never a pass.

Tests that need Docker and the pinned image skip, never pass, when either is
absent. They skip on hosted CI, so the isolation properties above are not
re-verified there. The real image build runs only with `AI_DLC_EVAL_BUILD=1`.

The candidate image is an equivalent install of the engine wheel with locked,
hash-verified dependencies on the base image's Python. It is not a run of
`bootstrap.sh`, so these evaluations say nothing about bootstrap.

## Running an evaluation

Docker must be on `PATH`. Images are never pulled: pull the digest-pinned base
yourself first.

```sh
BASE=python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
docker pull "$BASE"
ai-dlc eval image --base "$BASE" \
  --profile evaluations/profiles/local-deterministic.json \
  --write evaluations/profiles/local.resolved.json
ai-dlc eval plan evaluations/suites/smoke.json --profile evaluations/profiles/local.resolved.json
ai-dlc eval run evaluations/suites/smoke.json \
  --profile evaluations/profiles/local.resolved.json --out /tmp/eval-run
ai-dlc eval report /tmp/eval-run
```

- `eval image` builds the wheel from the checkout, installs it on the base image,
  checks that the result is the base plus added layers and that `ai-dlc --version`
  runs offline, and writes a copy of the profile bound to that build. Do not
  commit the resolved profile; it names a local image.
- `eval plan` starts nothing and reads no secret. It refuses, naming the field,
  an unpinned image, a secret value in the profile, missing budgets, duplicate
  identifiers, or a scenario without both arms.
- `eval run` needs an empty `--out`. It refuses a treatment image that is not the
  baseline image plus layers, and a fixture whose content digest differs from the
  suite's.
- `eval report` rebuilds `report.json`, `report.junit.xml` and
  `report.timeline.md` from the run directory alone, without Docker or network.

## Reading a result

Each arm has one outcome:

| Outcome | Meaning |
| --- | --- |
| `completed` | every mandatory assertion passed |
| `product` | hidden tests failed |
| `workflow-violation` | the code is right but a mandatory workflow artifact is missing (treatment only) |
| `infrastructure` | provisioning, staging or installation failed; not the product's fault |
| `unavailable` | a mandatory observation could not be made |
| `incomplete` | timeout, cancellation, damaged or tampered evidence, or a leaked credential |

Quality assertions are always `pending`; only a person records them. Workflow
kinds without an observer (`ordering`, process and MCP observation) are
`unavailable`. The baseline arm is graded on correctness only.

The comparison gives, per scenario, hidden-test passes, turns and wall seconds
for each arm and their difference. Token and spend usage is `null` until a driver
reports it. With one attempt per arm the claim is `none`: a difference, not a
conclusion. Check `cleanup_clean` on every arm; `false` names the container or
volume to remove by hand from `cleanup-ledger.jsonl`.

## Known gaps

- `python:3.12-slim` has no Git, and `ai-dlc project adopt` fails without it.
  Real-client runs need a purpose-built, digest-pinned base image with Git and
  the client's prerequisites, shared by both arms (#138).
- No process, MCP or Git observer exists yet, so the only workflow assertion
  that can pass is `artifact-present`.
