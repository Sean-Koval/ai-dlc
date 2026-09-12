# Report a missing mise runtime from project check without a traceback

## Why
On 2026-09-11 a local `ai-dlc project check --required --json` for PR #46 crashed with an uncaught `RuntimeError` from `runtime_env` because the bootstrap bin directory was not on PATH. The CLI printed a traceback, stdout carried no valid JSON for a `--json` caller, and the message did not name the usual cause, an unactivated shell.

## What Changes
- A missing configured runtime SHALL fail `project check` with a nonzero exit, one concise message and an activation remedy, without a traceback.
- JSON output SHALL remain valid, SHALL NOT claim that any check ran, and no receipt SHALL be written as if checks passed.

## Capabilities
### Modified Capabilities
- connected-project-readiness: An unavailable runtime is an actionable scoped failure rather than an uncaught error.

## Impact
Project check entry point, the shared project runtime resolution and their tests. No check command, receipt contract for executed checks, bootstrap behavior or shell configuration is changed automatically.
