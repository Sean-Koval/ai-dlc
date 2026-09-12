# Keep source bootstrap from repointing the global ai-dlc aliases

## Context
`$AI_DLC_BOOTSTRAP_HOME/bin/ai-dlc` is one machine-wide selection shared by every shell, while source mode deliberately keeps one environment per checkout keyed by the checkout path. Publishing the alias unconditionally made a per-checkout preparation step rewrite that shared selection, and nothing recorded which checkout the alias had come to run.

## Goals / Non-Goals
Make the shared selection a deliberate choice and make its current owner observable. Do not change release-mode publication, remove or repair an alias automatically, stop preparing a per-checkout environment, or require the alias in order to use a checkout.

## Decisions
- Publish in source mode only on `--publish-aliases`, or when no working alias exists. A first bootstrap on a fresh machine must still produce a usable `ai-dlc`, and a broken alias is not a selection worth preserving.
- Record the checkout inside the environment it describes (`ai-dlc-source-root`), not beside the alias. The record then cannot outlive or misdescribe the environment the alias resolves into.
- Attribute the alias by resolving it to its environment and reading that record, rather than reversing the path checksum in the environment's name. Attribution stays unknown when no record exists instead of being guessed.
- Report an alias that runs another checkout as an activation finding, because that is what the observed failure looked like from inside a session.
- Rejected: publishing per-checkout alias names, which multiplies machine-wide names for one selection. Rejected: refusing to bootstrap when another checkout owns the alias, which would block preparing a worktree at all.

## Risks / Trade-offs
A session that relied on bootstrap repointing the alias must now pass `--publish-aliases` or use the checkout's own environment; bootstrap output names both. Environments prepared before this change carry no checkout record, so their alias stays unattributed until bootstrap runs again.

## Migration Plan
No migration is required. Existing aliases keep working and are left alone; rerunning bootstrap in a checkout records that checkout, and `--publish-aliases` reproduces the old behavior.
