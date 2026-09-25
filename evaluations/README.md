# Engine evaluations

Maintainer-only inputs for `ai-dlc eval`. This directory is deliberately outside
the wheel: `hidden/` holds controller-side acceptance tests and reference
solutions that an attempt must never be able to read.

- `suites/` scenarios; fixture paths resolve beside the suite file and are bound by content digest.
- `fixtures/` the project an agent is given.
- `hidden/` acceptance tests and a reference solution, used only by the grader.
- `images/` recipes for the base image both arms share (`ai-dlc eval base`).
- `profiles/` execution profiles. `local-deterministic` exercises the runner and
  grader with a scripted driver: it writes the reference solution in the
  treatment arm only, so its result says nothing about AI-DLC. Its `engine.image`
  is a placeholder.

## Run it

```sh
BASE=python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
docker pull "$BASE"                       # run never pulls
ai-dlc eval image --base "$BASE" \
  --profile evaluations/profiles/local-deterministic.json --write /tmp/profile.json
ai-dlc eval run evaluations/suites/smoke.json --profile /tmp/profile.json --out /tmp/eval-run
ai-dlc eval report /tmp/eval-run          # rebuilds offline
```

`--write` resolves `driver.script` beside the written profile, so either write it
next to the script or make `driver.script` absolute. `local-candidate.script.json`
additionally checks that `ai-dlc` runs in the treatment arm and is absent from the
baseline arm; it needs a real candidate image.

The Claude Code driver and its current qualification limits are documented in
[the evaluation runbook](../docs/verification/end-to-end-evaluation.md#claude-code-driver-task-4).
Run-wide budgets, treatment adoption and Git observation are implemented.
`suites/real-client.json` uses the same neutral CSV goal with Git workflow
assertions; the original `smoke.json` remains the deterministic machinery check.
The paid comparison is deferred, and the wheel-only candidate image still needs
a prepared runtime for its declared project checks; see the runbook before a real
comparison. Use the deterministic profile without model charges.
