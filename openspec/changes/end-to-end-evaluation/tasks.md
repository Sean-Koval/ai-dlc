# End-to-end evaluation, increment 1

Goal: Deliver #137 plus a baseline arm; leave #138–#141 open.
Architecture: `verification/evaluation/` owns contracts, planning, the attempt
lifecycle, observation and reporting; `cli.py` delegates. Reuse `sandbox.py` controls.
Spec: [requirements](specs/end-to-end-evaluation/spec.md) and [design](design.md).

- [x] 0. Update #137's body to include the baseline arm (EE-05), which the
  maintainer confirmed on September 18, 2026.
- [x] 1. Add the four schemas under `contracts/` and failing tests in
  `tests/test_evaluation_planning.py` for version, secret-free and arm validation.
- [x] 2. Implement `eval plan` offline: expand the scenario, arm and attempt
  matrix, resolve the installation source and budgets, and refuse on missing
  fields without reading credential values or starting Docker.
- [ ] 3. (Lifecycle, deterministic steps, limits, cancellation, evidence and
  cleanup delivered; the recipe that builds the candidate image from a wheel
  remains, see design.)
  Implement the attempt lifecycle and deterministic driver. Add Docker
  integration tests for fresh state per attempt, wheel installation through
  bootstrap, timeout, cancellation, resource limits, evidence before cleanup and
  retained cleanup failure. Mark them to skip, not pass, without Docker.
- [x] 4. Add the CSV fixture and controller-side hidden tests; implement the
  evaluator with separate dimensions and outcome classes.
- [x] 5. Add synthetic negative tests: forged completion text, missing mandatory
  observation, changed artifact, malformed or truncated events, hidden-test
  failure, secret in evidence, cleanup failure. None may produce a pass.
- [x] 6. Implement `eval report` reconstruction (JSON, JUnit, timeline) including
  the per-scenario arm comparison.
- [ ] 7. Document the commands in the verification runbook, enroll catalog and
  code mappings, run required checks, record documentation dispositions, archive.
