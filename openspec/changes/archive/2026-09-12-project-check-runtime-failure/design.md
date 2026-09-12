# Report a missing mise runtime from project check without a traceback

## Context
`project check` resolves a runtime environment before running any configured check. With `mise` selected and absent from PATH, `runtime_env` raises a bare `RuntimeError`. Typer lets it escape, so the process exits with a traceback, and `--json` consumers receive no parsable object.

## Goals / Non-Goals
Make an unactivated or unbootstrapped shell obvious and actionable, and keep `--json` parsable on that path. Do not install tools, modify PATH, repair shell configuration, relax the runtime requirement, or change the receipt contract for checks that actually ran.

## Decisions
- Raise a dedicated `RuntimeUnavailable` error from the runtime resolution instead of a bare `RuntimeError`, so the entry point can distinguish a missing runtime from a check failure.
- Carry the missing executable and an ordered remedy list on the error, and let the CLI render them; the service does not format CLI output.
- Emit a structured failure object with an explicit empty outcome list and `ran = false`, so no consumer can read it as a passing or partial run.
- Write no receipt on this path: a receipt names executed checks, and none executed.
- Rejected: catching every exception at the entry point, which would hide genuine defects behind a remedy that does not apply. Rejected: falling back to the ambient environment without `mise`, which would run checks against unpinned tool versions.

## Risks / Trade-offs
A caller that parses only `outcomes` sees an empty list; the nonzero exit and explicit `ran` field keep the failure visible. Other runtime preparation failures keep their current behavior until they are given the same treatment.

## Migration Plan
No configuration or receipt migration. Existing passing runs are unaffected; previously crashing runs now exit nonzero with parsable output.
