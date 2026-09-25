# End-to-end evaluation verification

`ai-dlc eval` runs the same task twice in isolated containers, once with the
engine installed (`treatment`) and once without it (`baseline`), grades both with
tests the attempt can never read, and reports the difference. It is a maintainer
tool. Its inputs live in [`evaluations/`](../../evaluations/README.md), outside
the wheel.

## Current evidence and its limit

As of September 19, 2026 the runner, grader, report and candidate-image recipe
are delivered and verified on one machine (WSL2 Ubuntu 22.04, Docker 26.1.3). The
original driver was `deterministic`: a script of fixed steps. The Claude Code
driver is now implemented with recorded-stream and mocked-container tests,
described below; `codex` remains unsupported. The shipped script writes
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
| `not-started` | the run budget refused this planned attempt before any attempt resources or client session started |

Quality assertions on executed attempts are `pending`; only a person records them.
All assertions on a `not-started` attempt are `unavailable`, and JUnit marks them
`skipped`. They cannot contribute correctness successes, including scenarios with
no mandatory correctness assertions. Workflow
kinds without an observer (`ordering`, process and MCP observation) are
`unavailable`. The baseline arm is graded on correctness only.

The comparison gives, per scenario, hidden-test passes, turns and wall seconds
for each arm and their difference. `metrics.usage` is total tokens and
`metrics.cost_usd` is client-reported spend; both remain `null` for the
deterministic driver. Claude Code reports its native turn count, token categories
and session identity under `metrics.client`. Missing or damaged client metering
is unknown, including turns; it is never zero usage. With one attempt per arm the claim is `none`: a difference, not a
conclusion. Check `cleanup_clean` on every arm; `false` names the container or
volume to remove by hand from `cleanup-ledger.jsonl`.

## Base image for real clients

`ai-dlc eval base evaluations/images/claude-code.json` builds the image both
arms share: the pinned Python parent, Git, and the Claude Code native binary at
the recipe's version. The controller downloads the binary, refuses bytes whose
sha256 differs from the recipe, and copies it in; the build needs no BuildKit.
Git and the client are then run offline as uid 1000. Pass the printed image ID to
`eval image --base` to build the candidate on top.

Verified September 20, 2026: base built with Git 2.47.3 and client 2.1.220; the
candidate built on it; `ai-dlc project adopt --apply` ran offline inside it.
Distribution packages are not version-pinned, so rebuild both images together
and never compare runs made on different base image IDs. The real build runs in
tests only with `AI_DLC_EVAL_BUILD=1`.

## Restricted network for real clients

A profile may declare `egress = {hosts, proxy_image}`. Each attempt then joins a
per-attempt internal Docker network whose only other member is a hardened,
digest-pinned allow-listing proxy; port 443 to the named hosts is the only way
out. The proxy's decisions are retained as `egress.jsonl`, and refused hosts
appear in the report as `metrics.egress_refused` and in the timeline. `eval plan`
refuses `egress` with the deterministic driver, which always runs with no network.

Verified September 20, 2026 with real Docker: direct traffic blocked, a listed
host connects, an unlisted host gets 403 and is logged, nothing left behind. No
paid client run has qualified the driver through this proxy yet. The allow-list
limits destinations, not what is sent to them.

## Claude Code driver (task 4)

A real-client profile uses `driver = {kind: "claude-code", version: "2.1.220"}`,
`model = "claude-sonnet-4-6"` (a full identifier, no short alias),
`credentials = ["ANTHROPIC_API_KEY"]`, and the restricted `egress` declaration
above. Its baseline image must contain that exact client; its treatment image
must extend that baseline. Planning records the same version, model and SHA256
of the scenario goal for both arms without reading credentials. At run time,
the API key must be set in the controller environment. Only the model-session
`docker exec` receives the key, by environment-variable name; the value is not
put in the command, profile or plan. Subscription credentials are unsupported.

The driver checks `claude --version` before starting the session, then uses
`-p --output-format stream-json --verbose --include-partial-messages` with the
unchanged goal as one argument. It loads project/local settings and guidance,
uses `bypassPermissions` inside the existing disposable non-root container,
and disables session persistence, updates and nonessential traffic. No host
configuration is mounted and no system-prompt text is added. The driver does
not perform treatment adoption yet; that is task 7.

Each attempt retains `client-version.txt` and `client-stream.jsonl`, including
partial bytes on timeout/cancellation. A credential leak is redacted and makes
the attempt incomplete; this is the deliberate exception to verbatim retention.
The parser validates the init/result identity, assistant and message-start
response models, and final per-model usage identities against the pinned model.
Native final usage includes cache creation and cache reads. Partial message usage is not summed again.
Malformed JSON/UTF-8, inconsistent identity, a missing final result or missing
mandatory usage makes the attempt incomplete and prevents passing assertions.
Terminal limit errors retain known usage. A partial stream cannot hide a
controller-observed memory failure or nonzero exit: raw evidence and the original
limit/exit diagnosis are both retained. Reports reparse this evidence offline;
client prose never grades the collected code.

`limits.max_turns` sets the client turn limit. An optional scenario
`limits.max_spend_usd` sets its spend cap (default USD 2, capped by the declared
run spend budget). The runner narrows this cap again to the remaining run spend
before each session. These are client limits, not a guarantee that an in-flight
API request cannot exceed the cap. Multi-turn declared answers are not delivered. Reports remain labelled `fixture`: a real client
alone does not qualify the fixture providers or prove AI-DLC's value.

Verified September 24, 2026: both-arm execution, credential isolation, raw
retention, independent grading/report rebuilds and negative stream cases through
mocked Docker boundaries. The committed stream was captured from the checksum-
verified native Darwin arm64 client 2.1.220 against a loopback fake API with a
dummy key (capture timestamp September 25 UTC). Only machine paths were
normalized; provenance is in `tests/test_evaluation_claude.py`. No model service
was called. This confirms native stream shape, not live billing or Docker client
connectivity. The same day's independent Docker base-image test passed on
macOS with Docker 20.10.17, Linux arm64; it verifies the Git/client image only.

The implementation follows the vendor's [headless stream documentation](https://code.claude.com/docs/en/headless)
and [CLI flags](https://code.claude.com/docs/en/cli-reference), checked against
the pinned client. In particular, it does not use newer flags that 2.1.220 lacks.

## Run budgets (task 5)

The runner uses one sequential ledger for all scenarios and both arms. Before
an attempt starts, both remaining run budgets must be positive and at least the
largest corresponding consumption observed in any earlier attempt. Positive
remaining budget exactly equal to the observed maximum permits one attempt;
exhausted budget permits none. Spend arithmetic uses decimal values, avoiding
binary rounding at boundaries such as USD 0.3 minus three USD 0.1 sessions.
Zero run tokens, zero run spend, or a zero scenario spend cap starts no client.
The deterministic driver retains its conventional zero-budget behavior.

Consumption comes from the validated final native result, counting input, output,
cache creation and cache read tokens once. Terminal errors still consume their
reported usage. Missing or malformed usage, and credential redaction, block later
client attempts conservatively; the original attempt keeps its resource, stream
or credential diagnosis. Budgets are never silently raised to finish the matrix.

Each real-client attempt retains a `budget.json` decision, covered by its evidence
manifest. Reports replay decisions in planned order against earlier trusted native
usage. A refused attempt has only its decision, attempt record and manifest;
missing, malformed, contradictory or extra execution evidence makes it
`incomplete`. Attempt records must carry the planned identity and a recognized
outcome; malformed consumed fields cannot bypass validation or crash rebuilding.
Older records may omit optional diagnostics and cleanup fields. Reports give every
planned row, plus per-arm `attempts_not_started`
and `attempts_incomplete` counts alongside the planned `attempts_per_arm`. All
measurements for refused rows are `null`, so they do not lower mean time or usage.
Tampering with earlier usage also invalidates dependent refusal receipts. These
hashes detect damage, not an adversary who consistently rewrites the whole run.
Older real-client recordings without decision receipts cannot establish the new
budget contract and rebuild as incomplete; deterministic reports remain supported.

**This is an observed-usage scheduling rule, not a strict billing ceiling.** The
first attempt has no observed maximum and may start with any positive run budget;
future attempts can consume more than any earlier one. Claude Code 2.1.220 exposes
no hard total-token cap. Its spend limit may overshoot while a request is in flight.
Actual reported overruns are retained without clipping, and subsequent attempts
are refused. Three attempts per arm at the recommended USD 2 attempt cap can
exceed the recommended USD 10 run allocation; inspect refused coverage and do not
interpret an unequal or incomplete matrix as a completed comparison.

Verified with recorded native streams and mocked Docker boundaries: zero and exact
boundaries, independent token/spend exhaustion, changing native spend caps,
multiple scenarios and arms, terminal errors, unknown usage, overruns, offline
reconstruction and damaged refusal evidence. No paid calls or live billing
qualification were performed for this change. Treatment adoption, the Git
observer and the real comparison remain tasks 6–8.

## Known gaps

- No process, MCP or Git observer exists yet, so the only workflow assertion
  that can pass is `artifact-present`.
