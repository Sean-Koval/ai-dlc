## Decisions

**Controller outside, agent inside.** The controller, expected answers, hidden
tests and evidence collector run on the host. The attempt container receives only
the fixture project, the declared goal and, for the treatment arm, the candidate
wheel and bootstrap script. Evidence is copied out before cleanup; a failed
cleanup is recorded, never hidden. There is no host fallback: missing Docker is an
`infrastructure` outcome.

**Arms.** A scenario is run once per arm per attempt. `treatment` installs the
candidate through `scripts/bootstrap.sh` from a wheel (never a mounted checkout)
and runs `project adopt` and `agents render`. `baseline` uses the same image
digest, fixture commit, goal text, bounded answers, limits and driver with no
AI-DLC installation or generated guidance. Workflow assertions apply only to
`treatment`; correctness assertions and usage apply to both. This mirrors the
control and treatment design already used by the skill evaluation (EV-01).

**Contracts.** Four JSON Schemas, each with a `schema` version: *scenario* (goal,
fixture reference, bounded answers, checkpoints, assertions, limits, arms);
*profile* (driver or client identity and version, model, engine artifact hash,
credential environment-variable names, permitted resources, budgets); *event*
(normalized timeline entry with source, timestamp, kind, evidence reference);
*report* (per-attempt, per-arm results). Scenarios and reports never contain
secret values; profiles name environment variables only.

**Results.** Each arm reports three independent dimensions: `workflow`,
`correctness`, `quality`. Each assertion stores expected condition, observation
and evidence references. A dimension is `pass`, `fail`, `unavailable` or
`pending`; `quality` is always `pending` until a human records it. An attempt's
outcome class is one of `completed`, `infrastructure`, `product`,
`workflow-violation`, `unavailable`, `incomplete`. A missing mandatory observation
yields `unavailable` or `incomplete`, never `pass`. The report also states, per
scenario, the treatment-minus-baseline difference in correctness, turns, wall time
and metered usage, with the attempt count beside it; it draws no significance
claim from fewer than the declared attempts.

**Driver.** The first driver is deterministic: a scripted command sequence per
arm that exercises provision, install, run, interrupt, collect and cleanup.
It exists to prove the runner, not to evaluate an agent. Client adapters plug in
behind the same driver interface in #138.

**Fixture.** One small Python CSV-validation project with a precise feature
request. Hidden acceptance tests live with the controller and are run against the
collected working tree after the attempt, in a separate container.

**Limits.** Defaults are 30 minutes and 20 turns per attempt. Model, token and
spend settings are explicit in the profile. Reports state which limits were
enforced and which were only metered.

**Reports.** `eval report` rebuilds JSON, JUnit and a readable failure timeline
from the retained run directory without launching anything. A run directory
records image digest, architecture, engine, driver and model identities, inputs,
events, hashes, diffs, hidden-test output, usage and cleanup status, which is
enough to rerun the same scenario against another wheel.

## Decisions made during increment 1

- An arm is a name, not an object. Because a scenario cannot express a per-arm
  goal, fixture, answer or limit, "arms differ in anything else" is refused by the
  contract itself, and every scenario must declare both arms. The baseline attempt
  plans with no engine artifact; workflow assertions are omitted from it.
- Planning refuses credential-shaped keys and recognizable token formats in a
  suite and names the field, never the value. It is a tripwire, not proof of
  absence; the run-time check against profile-named variables (EE-04) is the real
  control.
- Schemas are generated from Pydantic models into `contracts/evaluation/` and
  checked by `scripts/check_generated.py`, matching the provider contracts.
- Suites and profiles load from JSON or TOML by file extension.

## Decisions made during increment 2 (attempt lifecycle)

- The project lives in a per-attempt Docker volume, not a tmpfs or a host mount.
  After a timeout or cancellation the controller stops the agent's container and
  a separate read-only collector container archives the volume, so evidence
  survives the agent's death and the agent cannot influence collection. A
  controller-owned stager is the only root process and exits before the agent
  starts. Nothing from the host is mounted.
- The agent runs as uid 1000 with no network, a read-only root, all capabilities
  dropped, no-new-privileges, and memory and process limits. Home is a fresh
  tmpfs. Disk is not enforced: the local volume driver has no quota, so the
  result lists it as metered by collection size only.
- Collected archives are unpacked with the `data` tar filter; an archive that
  tries to leave the run directory makes the attempt `incomplete` at `collect`.
- Driver-level outcomes are `completed`, `infrastructure` (Docker missing,
  provisioning, installation, memory limit) and `incomplete` (timeout,
  cancellation, a failed step, unreadable evidence). `product` and
  `workflow-violation` belong to the evaluator in the next increment.
- Removal failures are recorded per resource in the result and in
  `cleanup-ledger.jsonl`; one failed removal does not skip the others.
- Real-Docker tests use a digest-pinned image that must already be present and
  are skipped, never passed, otherwise. They never pull, so required CI does not
  depend on a registry; on hosted runners they currently skip.

**Decided September 18, 2026: the candidate is prebuilt into an image.**
`scripts/bootstrap.sh` installs only from a checkout or from a published HTTPS
release, and that HTTPS-only rule is a security property that testing should not
loosen. The treatment arm therefore runs a prebuilt candidate image, and EE-02 and
EE-05 were amended: the run inspects both images and refuses unless the treatment
image is the baseline image plus added layers, which keeps "differs only in
AI-DLC" mechanically checkable. Registry digests and local image IDs are both
accepted as pins, because a candidate image is normally built locally. The
recipe that builds that image from a wheel is the remainder of task 3.

## Decisions made during increment 3 (fixture, evaluator, run)

- Evaluation inputs live in top-level `evaluations/`, which the wheel does not
  package. `agents/` ships inside the wheel, so hidden tests placed there would
  be readable inside a treatment attempt. A test guards the packaging.
- Fixtures are bound by a content digest over relative paths and file bytes, not
  a Git revision, so a fixture can live in this repository and ignore timestamps.
- Hidden tests are graded in a separate network-less container on the baseline
  image, from the collected tree plus the controller-held tests. The result file
  is the only correctness evidence; step output is never read by the evaluator.
- Implemented observers: `hidden-tests` (correctness) and `artifact-present`
  (workflow, a glob over the collected project). Any other kind is `unavailable`
  until #138 adds process and MCP observers. Quality is always `pending`.
- Attempt outcome: a driver-level failure stands; otherwise a mandatory
  correctness failure is `product`, a mandatory workflow failure is
  `workflow-violation`, and a mandatory unavailable observation is `unavailable`.
- A run retains `plan.json`, the suite, profile and script under `inputs/`, and
  per attempt its inputs, events, steps, collected tree, grading and arm report.
  `run` refuses a non-empty output directory and images that are not present
  locally; it never pulls.
- The shipped `local-deterministic` profile writes the reference solution in the
  treatment arm only. It proves the runner and grader, and its report is labelled
  fixture evidence with no comparison claim.

## Decisions made during increment 4 (report and hardening)

- `run` and `report` share one builder. `run` grades once, retains the grader's
  output, then calls the same offline builder that `report` uses, so a rebuilt
  report equals the original by construction. The builder starts no process and
  opens no socket.
- Each attempt directory carries a manifest of file hashes. A changed, missing or
  extra file, a malformed or truncated event trace, or a missing attempt record
  makes the attempt `incomplete`, names the files, and turns every non-pending
  result into `unavailable`. The manifest detects accidental and partial changes;
  it is not a signature and does not detect someone who rewrites it too.
- Values of profile-named credential variables found in retained evidence are
  replaced with `[REDACTED:<NAME>]`, the attempt becomes `incomplete` at stage
  `redaction`, and the detail names the variable and files, never the value.
  Values shorter than eight characters are ignored to avoid shredding ordinary
  text. This is the run-time control that planning's tripwire anticipates.
- The comparison states, per scenario, attempts passing all mandatory correctness
  assertions, mean turns, mean wall seconds and usage for each arm with the
  treatment-minus-baseline difference. Usage is null unless a driver meters it.
  A cleanup failure is reported on the arm; it never upgrades or hides a result.
- JUnit maps fail to failure, unavailable to error and pending to skipped. The
  timeline lists controller events and assertion evidence; step output is never
  quoted.

## Decisions made during increment 5 (candidate image)

- `ai-dlc eval image --base <pinned image>` builds the wheel with `uv build`,
  exports locked hash-pinned constraints exactly as the release workflow does,
  and installs them with `--require-hashes` followed by the wheel with
  `--no-deps` inside `docker build` on the baseline image. The build context
  holds only the Dockerfile, the constraints and the wheel; the checkout is never
  copied. The command verifies that the result is derived from the baseline image
  and that `ai-dlc --version` runs with no network, and returns the image ID and
  the wheel's hash. `--profile` with `--write` binds a copy of a profile to the
  build; the source profile is not edited.
- This is an equivalent engine install, not a run of `scripts/bootstrap.sh`. The
  base image's Python is used and bootstrap's managed Python, uv and mise are
  absent, so an evaluation says nothing about bootstrap itself; the release
  workflow's install verification and `verify-published` cover that path.
- The real build needs a package index and is opt-in in tests
  (`AI_DLC_EVAL_BUILD=1`). Attempts never have a network.

**Finding for #138.** `python:3.12-slim` has no Git, and `ai-dlc project adopt`
fails inside it with "git is not available". A real-agent journey needs a
purpose-built, digest-pinned base image containing Git (and whatever a coding
client needs) that both arms share; the candidate image is then built on that.

## Not decided here

Real client adapters, fake and live providers, recovery journeys, CI lanes and
release policy (#138–#140). Whether to build them depends on what the first
treatment-versus-baseline report shows.
