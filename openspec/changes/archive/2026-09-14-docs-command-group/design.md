# Fold the documentation commands into `ai-dlc docs`

## Context
The twelve `project docs-*` commands are thin Typer wrappers over `ai_dlc.documentation` services that MCP also exposes as `project_docs_*` tools. Nothing in the services depends on the CLI names. The workspace diagnostics service probes `ai-dlc project --help` for the tokens `docs-search`, `docs-read` and `workspace-check` to decide whether an installed CLI is current; it is a function under `src/ai_dlc/documentation/` and stays untouched in this change.

## Goals / Non-Goals
Give the documentation workflow one short group whose help lists six commands, keep every existing invocation and test working for one release, and rename every current mention. Do not change any service function, evidence format, gate rule or MCP tool name. Do not create `design` or `tracker` groups: they are already gone and an empty group must not ship.

## Decisions
- One private helper per service call in `cli.py`; the six new commands and the twelve hidden aliases call the same helpers, so an alias cannot drift from its replacement. The aliases are registered with `hidden=True` and print exactly one line to stderr through a shared `_deprecated` helper naming the replacement; stdout and the exit status are untouched so existing callers that parse JSON keep working.
- `docs check` chooses one mode: plain ownership/link inspection, `--inventory`, or `--style --path ...`. The two flags are mutually exclusive and `--style` requires at least one `--path`; the CLI reports a usage error before any service runs. `--strict` keeps its meaning for the check and style modes.
- `docs review` chooses one mode from `--disposition`, `--baseline`, `--report` and `--check`; none means impact inspection. Each mode's required options are validated in the CLI (`--decisions` is implied by `--disposition FILE`; `--baseline` needs `--owner` and `--reason`; `--report` needs `--path`; `--check` needs `--packet` and `--review`) and a mode-specific option given without its mode is a usage error. `--base` is required by every mode except `--baseline` and `--check`, which never read a comparison.
- `ai-dlc project --help` gains an epilog naming the move to `ai-dlc docs`. The epilog lists the legacy names, so the workspace diagnostics probe, which matches those tokens in the `project` help text, still reports an installed CLI as current without changing the diagnostics service. Repointing that probe at `docs --help` is a follow-up once the aliases are removed.
- The service module strings that still say `ai-dlc project docs-check` (`moc.py`, `workspace_diagnostics.py`) stay as they are: the alias keeps working for this release and the rule for this change is to leave `src/ai_dlc/documentation/` untouched.
- Rejected: leaving the aliases visible in `project --help`. That would keep twenty-five entries on the list the issue measured. Rejected: one `docs review` subcommand per legacy verb. That would recreate the original breadth under a new prefix.

## Risks / Trade-offs
Mode validation lives in the CLI, so the MCP tools, which take explicit parameters per operation, remain the precise surface and the CLI stays a convenience. A caller that scrapes `project --help` for the legacy names still finds them in the epilog until the aliases are removed.

## Migration Plan
Downstream projects change `documentation = "ai-dlc project docs-gate"` to `ai-dlc docs gate` in their check manifest at their own pace; the alias keeps the old line working for one release and prints the replacement. The project template ships the new names.
