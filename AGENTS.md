# Repository guidance

AI-DLC is a Python scaffolding and harness-configuration framework. It prepares
tools and guides agents; it is not a hosted autonomous development orchestrator.
CLI and MCP entry points share application services. Provider details belong behind
contracts; credentials and machine paths never belong in shared configuration.

Before preparing this checkout, identify the intended repository. A teammate who
cloned AI-DLC only to install it for another project should follow the consumer
route in [README.md](README.md#get-started), pass that work repository explicitly
to `project onboard --root`, and keep this engine checkout's providers and accounts
out of the target. Native Windows consumer installation is unsupported in this
revision; [#172](https://github.com/Sean-Koval/ai-dlc/issues/172) tracks installation
and [#53](https://github.com/Sean-Koval/ai-dlc/issues/53) tracks client/cross-machine
qualification. Do not present the POSIX bootstrap below as native Windows guidance.
Only contributors changing AI-DLC itself should prepare this checkout and run its
full required checks.

Prepare this checkout with `sh scripts/bootstrap.sh --source`; run
`ai-dlc project check --required`. That prepares this checkout's own environment
and leaves the shared `ai-dlc` alias alone; use the printed environment path, or
pass `--publish-aliases` to repoint the alias deliberately. Use the Python implementation in `src/ai_dlc/`.
The [architecture](docs/architecture.md) maps its packages and entry points.
The Rust implementation is retired and removed; its plans stay in `docs/archive/`.
`templates/` still supplies the supported legacy scaffold command. Preserve
compatibility tests and packaged assets.

## Placement and upkeep

- Read [docs/index.md](docs/index.md) before creating documentation. Update the
  canonical explanation instead of adding another summary or completion report.
- Keep proposal, design, requirements and tasks together in `openspec/changes/`.
  Keep durable explanations in `docs/design/`, procedures in `docs/runbooks/` or
  `docs/workflows/`, and actual qualification evidence in `docs/verification/`.
- `docs/archive/` preserves explicitly historical material. Its old commands and
  tool instructions are not current guidance. Never manufacture review freshness.
- Keep disposable execution logs in ignored `.ai-dlc/local/`; do not create root
  planning files, `.superpowers/`, or tool-specific planning hierarchies.
- Enroll durable documents in `docs/catalog.toml`; update code mappings and links
  when moving sources. Record a documentation-impact disposition for changes.
- Put new Python modules in the responsible subpackage; keep CLI/MCP thin and
  provider-specific logic inside adapters. Do not infer dead code from filenames.
- Project templates and portable skills serve downstream projects. Keep their
  setup guidance generic; never embed this repository's personal account choices.

Use conventional commit prefixes. Test observable changes and preserve ownership,
recovery and configuration boundaries. Mocked tests do not prove live platform
qualification; consult [release gates](docs/release-verification.md). Do not
publish packages or mutate remote services implicitly.

<!-- ai-dlc:begin 4f502112de19d54b6787c6ccf72414a9dcfa8c33c07aeb7ab02ccf08884c1639 -->
# Shared project guidance

Read ai-dlc.toml and the active .ai-dlc/work record, if present, before work.
Use specification artifacts for implementation tasks; finalize required specifications before review and follow the selected specification provider's instructions.
Use the selected tracker for priority and status; follow its provider instructions.
Archive OpenSpec changes on the bound delivery branch before merge with `ai-dlc work archive`.
Immediately before merge, update from the target branch and rerun required checks.
Record documentation dispositions again only for targets the required documentation gate reports stale.
Complete work through `ai-dlc work finish`.
Finish from a checkout at the merge commit; when the target branch has moved, prepare a temporary detached worktree at that commit, finish there, then remove it.
Store architecture, design, decisions and runbooks in docs/.
Keep personal notes in the selected knowledge provider and follow its instructions.

## Verification

- layout: `uv run --locked --no-sync python scripts/check_layout.py`
- generated: `ai-dlc agents render --check && uv run --locked --no-sync python scripts/check_generated.py`
- format: `uv run --locked --no-sync ruff format --check src tests scripts`
- lint: `uv run --locked --no-sync ruff check src tests scripts`
- types: `uv run --locked --no-sync pyright --pythonpath .venv/bin/python`
- test: `uv run --locked --no-sync pytest -q`
- documentation: `ai-dlc docs gate`
- work-records: `ai-dlc work validate --all`

Run `ai-dlc project check --required` in the prepared project environment.

## Selected providers and tools

Read the linked instructions for each configured provider before using its tools.
Modules name installation requirements; their presence does not establish account
access or platform qualification. Run `ai-dlc project readiness --root .` for
offline requirements and use doctor for explicit provider health inspection.

- scm: github (modules: core); [providers/github.md](<.ai-dlc/providers/github.md>)
- tracker: github-issues (modules: core); [providers/github-issues.md](<.ai-dlc/providers/github-issues.md>)
- deploy: none (modules: none); [providers/none.md](<.ai-dlc/providers/none.md>)
- knowledge: obsidian (modules: none); [providers/obsidian.md](<.ai-dlc/providers/obsidian.md>)
- specs: openspec (modules: openspec); [providers/openspec.md](<.ai-dlc/providers/openspec.md>)
<!-- ai-dlc:end -->
