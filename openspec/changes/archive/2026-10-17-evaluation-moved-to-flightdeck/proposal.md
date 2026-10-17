# Evaluation moved to flightdeck

## Why

ADR 0001 makes flightdeck the only harness judge. AI-DLC's end-to-end evaluation runner (`ai-dlc eval`), its contracts and assets, and the prompt-only skill evaluation were frozen and inventoried for the port in #194, and flightdeck now carries the ported local runner. Keeping two runners would let them diverge, so AI-DLC removes its copy (#195).

## What Changes

- Remove `src/ai_dlc/verification/evaluation/`, `harness/skill_evaluation.py`, `providers/evaluation_api.py`, `scripts/run_skill_evaluation.py`, `contracts/evaluation/`, `evaluations/`, `agents/evaluation.toml`, `agents/evaluation-scenarios.json`, `agents/evaluations/` and their tests. `verification/test_proxy.py` stays for provider conformance.
- `ai-dlc eval` becomes a hidden stub that prints a pointer to flightdeck and tag `eval-handoff-2026-10` and exits 2, for one release.
- Retire the `end-to-end-evaluation` and `skill-evaluation` capabilities. OpenSpec cannot archive a delta that removes every requirement, so their last text is kept under `retired/` in this change and the spec directories are deleted.

## Impact

Maintainers run evaluations from flightdeck. The last AI-DLC version is tag `eval-handoff-2026-10`; see `docs/migration.md#ai-dlc-eval-removed`.
