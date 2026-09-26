# Concise team skill context

## Why

The team renderer duplicates every selected skill body into always-loaded project
guidance and into native skill files. Larger team collections increase repeated
context even when a task needs only one skill. Keep rules immediately available
and make skills discoverable without copying their instructions into every session.

## What Changes

- Render selected team skills as a concise index of name, source, description and
  working client-specific file links; retain full selected rule bodies.
- Keep complete skill files, source selection, pinned provenance and existing
  ownership/conflict/recovery behavior unchanged.
- Explain that agents should read the linked skill when it applies, including
  clients whose native discovery has not been verified. With no rendered client
  destination, retain inline skill bodies so access is not lost.
- Upgrade intact generated guidance on the next ordinary render, without a new
  configuration setting or a source-lock/ownership schema migration.
- Verify output bytes on reproducible fixtures; make no inferred token, cost or
  native-client qualification claim.

## Capabilities

### Modified Capabilities

- `team-sources`: clarify TS-02 skill appearance and add concise discovery,
  compatibility and measurable output requirements.

## Impact

Primary code: `src/ai_dlc/harness/team_source_render.py` and its call site in
`src/ai_dlc/harness/agents.py`. Tests: `tests/test_team_sources.py` and
`tests/test_native_harnesses.py`. Native client destinations remain those in
`CLIENT_SKILL_DIRECTORIES`; NH-01 and NH-03 remain in force.

Canonical operator guidance is
[the enrollment runbook](../../../docs/runbooks/machine-enrollment.md), especially
its current description of duplicated skill bodies. Review
[architecture](../../../docs/architecture.md) and
[release verification](../../../docs/release-verification.md) for affected mappings
and qualification limits; record content-bound documentation dispositions and
update [the catalog](../../../docs/catalog.toml) only if mappings change. No new
permanent guide or completion report is needed.
