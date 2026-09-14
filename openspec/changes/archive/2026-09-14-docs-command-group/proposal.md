# Fold the documentation commands into `ai-dlc docs`

## Why
`ai-dlc project` carries twenty-five subcommands and twelve of them are prefixed `docs-`. The breadth hides the three documentation commands people actually run (impact review, disposition recording and the gate) behind nine specialised names, and a command list that long reads as scope creep rather than a workflow. Issue #86 records the measurement.

The issue also names empty `docs`, `design` and `tracker` Typer groups. They were removed before this change started; `cli.py` registers only `project`, `work`, `agents`, `profile`, `setup`, `machine`, `knowledge`, `provider` and `mcp`. This change therefore creates the `docs` group fresh and ships no empty group.

## What Changes
- A new `ai-dlc docs` group SHALL expose exactly `check`, `review`, `gate`, `read`, `search` and `init`.
  - `docs check` is the former `docs-check`; `--inventory` runs the former `docs-inventory` and `--style` the former `docs-style`.
  - `docs review --base` is the former `docs-impact`; `--disposition FILE --reviewer NAME` records the former `docs-disposition`, `--baseline --owner --reason` proposes the former `docs-baseline`, `--report --path ...` prepares the former `docs-review` packet and `--check --packet --review` validates it as the former `docs-review-check`.
  - `docs gate`, `docs read`, `docs search` and `docs init` are the former `docs-gate`, `docs-read`, `docs-search` and `docs-init`, unchanged.
- Every former `ai-dlc project docs-*` command SHALL keep working for one release as a hidden alias that calls the same service and prints one deprecation line to stderr; its stdout and exit status are unchanged.
- This repository's required `documentation` check SHALL run `ai-dlc docs gate`; the rendered `AGENTS.md`, the project template's documentation guide, the tool maps and every current document that names a `docs-*` command SHALL name the new form.
- The MCP tool names (`project_docs_*`) and every function under `src/ai_dlc/documentation/` are unchanged.

## Capabilities
### Modified Capabilities
- documentation-impact-workflow: the shared CLI surface for impact inspection, disposition recording and the gate is `ai-dlc docs review` and `ai-dlc docs gate`; the legacy `project docs-*` names keep working with a deprecation notice.

## Impact
`src/ai_dlc/cli.py` (the documentation commands and group registration only), `ai-dlc.toml`, the rendered `AGENTS.md`, the shipped `document-organize` and `document-review` skills, the README, the documentation index, the tool maps and their template twins, the template documentation guide, the document-workspace qualification runbook, the local-and-shared-knowledge design and the documentation-workflow verification narrative. Documentation behaviour, evidence formats and gate rules do not change.
