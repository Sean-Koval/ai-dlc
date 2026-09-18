# Engine evaluations

Maintainer-only inputs for `ai-dlc eval`. This directory is deliberately outside
the wheel: `hidden/` holds controller-side acceptance tests and reference
solutions that an attempt must never be able to read.

- `suites/` scenarios; fixture paths resolve beside the suite file and are bound by content digest.
- `fixtures/` the project an agent is given.
- `hidden/` acceptance tests and a reference solution, used only by the grader.
- `profiles/` execution profiles. `local-deterministic` exercises the runner and
  grader with a scripted driver: it writes the reference solution in the
  treatment arm only, so its result says nothing about AI-DLC. Replace the
  placeholder `engine.image` with a prebuilt candidate image derived from `image`.
