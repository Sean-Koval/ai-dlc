# Repository guidance

AI-DLC is a Python scaffolding and harness-configuration framework. It prepares
tools and guides agents; it is not a hosted autonomous development orchestrator.
CLI and MCP entry points share application services. Provider details belong behind
contracts; credentials and machine paths never belong in shared configuration.

Prepare this checkout with `sh scripts/bootstrap.sh --source`; run
`ai-dlc project check --required`. That prepares this checkout's own environment
and leaves the shared `ai-dlc` alias alone; use the printed environment path, or
pass `--publish-aliases` to repoint the alias deliberately. Use the Python implementation in `src/ai_dlc/`.
The [architecture](docs/architecture.md) maps its packages and entry points.
`crates/` is historical Rust; `templates/` still supplies the supported legacy
scaffold command. Preserve compatibility tests and packaged assets.

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

<!-- ai-dlc:begin 28d30881639873ef66b4afd508bf5f2d540c271cfd7015021f61d3c1ba559b53 -->
# Shared project guidance

Read ai-dlc.toml and the active .ai-dlc/work record before work.
Use specification artifacts for implementation tasks and the tracker for priority/status.
Finalize required specifications before review. Complete work through ai-dlc work finish.
Immediately before merge, update from the target branch and refresh base-bound evidence and checks.
Store architecture, design, decisions and runbooks in docs/. Keep personal notes in knowledge.

## Verification

- layout: `uv run --locked --no-sync python scripts/check_layout.py`
- generated: `ai-dlc agents render --check && uv run --locked --no-sync python scripts/check_generated.py`
- format: `uv run --locked --no-sync ruff format --check src tests scripts`
- lint: `uv run --locked --no-sync ruff check src tests scripts`
- types: `uv run --locked --no-sync pyright --pythonpath .venv/bin/python`
- test: `uv run --locked --no-sync pytest -q`
- documentation: `ai-dlc project docs-gate`

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
