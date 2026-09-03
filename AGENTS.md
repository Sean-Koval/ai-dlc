# Repository guidelines

The current implementation is Python in `src/ai_dlc/`. CLI and MCP entry points share application services. Keep provider details behind contracts, credentials outside tracked configuration, and machine settings outside shared project files.

Prepare the checkout with `sh scripts/bootstrap.sh --source`. Run the required manifest checks using `ai-dlc project check --required`. Tests cover configuration boundaries, receipts, recovery, provider integrity, managed files, and legacy scaffold fixtures. Preserve historical Rust source; it is no longer the release packaging path.

Store durable architecture, decisions and runbooks in `docs/`; formal change artifacts belong in `openspec/`. Update tests for observable behavior. Never claim live service or platform verification from mocked fixtures. See `docs/release-verification.md` for outstanding release gates.

Use conventional commit prefixes. Describe behavior and validation in review descriptions; do not publish packages or change remote service state implicitly.

<!-- ai-dlc:begin e541af3871b392bd14df98af166a94c7b8d3e0eb8e06bfa0aadfba661b90ea45 -->
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
<!-- ai-dlc:end -->
