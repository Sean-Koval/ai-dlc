# Repository guidelines

The current implementation is Python in `src/ai_dlc/`. CLI and MCP entry points share application services. Keep provider details behind contracts, credentials outside tracked configuration, and machine settings outside shared project files.

Prepare the checkout with `sh scripts/bootstrap.sh --source`. Run the required manifest checks using `ai-dlc project check --required`. Tests cover configuration boundaries, receipts, recovery, provider integrity, managed files, and legacy scaffold fixtures. Preserve historical Rust source; it is no longer the release packaging path.

Store durable architecture, decisions and runbooks in `docs/`; formal change artifacts belong in `openspec/`. Update tests for observable behavior. Never claim live service or platform verification from mocked fixtures. See `docs/release-verification.md` for outstanding release gates.

Use conventional commit prefixes. Describe behavior and validation in review descriptions; do not publish packages or change remote service state implicitly.

<!-- ai-dlc:begin d29e768d7e0c5936752e7ef94193c3a12bc92cb405bc0284e543f76b19d7fd05 -->
# Shared project guidance

Read ai-dlc.toml and the active .ai-dlc/work record before work.
Use specification artifacts for implementation tasks and the tracker for priority/status.
Finalize required specifications before review. Complete work through ai-dlc work finish.
Store architecture, design, decisions and runbooks in docs/. Keep personal notes in knowledge.

## Verification

- generated: `ai-dlc agents render --check && uv run --locked --no-sync python scripts/check_generated.py`
- format: `uv run --locked --no-sync ruff format --check src tests scripts`
- lint: `uv run --locked --no-sync ruff check src tests scripts`
- types: `uv run --locked --no-sync pyright --pythonpath .venv/bin/python`
- test: `uv run --locked --no-sync pytest -q`

Run `ai-dlc project check --required` in the prepared project environment.

## Selected providers and tools

Read the linked instructions for each configured provider before using its tools.
Modules name installation requirements; their presence does not establish account
access or platform qualification. Run `ai-dlc project readiness --root .` for
offline requirements and use doctor for explicit provider health inspection.

- tracker: github-issues (modules: core); [providers/github-issues.md](<.ai-dlc/providers/github-issues.md>)
- specs: openspec (modules: openspec); [providers/openspec.md](<.ai-dlc/providers/openspec.md>)
- scm: github; unsupported: no component for provider: github
- deploy: none; unsupported: no component for provider: none
- knowledge: obsidian; unsupported: no component for provider: obsidian
<!-- ai-dlc:end -->
