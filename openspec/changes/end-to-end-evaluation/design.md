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

## Not decided here

Real client adapters, fake and live providers, recovery journeys, CI lanes and
release policy (#138–#140). Whether to build them depends on what the first
treatment-versus-baseline report shows.
