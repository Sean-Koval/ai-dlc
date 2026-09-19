# Engine evaluations

Maintainer-only inputs for `ai-dlc eval`. This directory is deliberately outside
the wheel: `hidden/` holds controller-side acceptance tests and reference
solutions that an attempt must never be able to read.

- `suites/` scenarios; fixture paths resolve beside the suite file and are bound by content digest.
- `fixtures/` the project an agent is given.
- `hidden/` acceptance tests and a reference solution, used only by the grader.
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
