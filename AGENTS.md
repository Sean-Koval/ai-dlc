# Repository Guidelines

## Project Structure & Module Organization
The workspace centers on `crates/ai-dlc-cli/`, which contains the Rust CLI (`src/main.rs`) and owns the embedded template loader. Provider-ready assets live under `templates/` (e.g., `templates/claude`, `templates/gemini`, `templates/roo`) and are bundled into the binary at build time. Configuration presets for external agents sit in `config/{claude-code, gemini-cli, roo-code}`. Planning notes, specs, and contributor docs land in `docs/` (see `docs/phase_1_rust.md` for the current roadmap), while experimental orchestration artifacts are parked in `coordination/`. Legacy Python-based smoke tests remain in `tests/cli/`; update or replace them when porting checks to Rust.

## Build, Test, and Development Commands
Use `cargo build` from the repo root to compile the CLI and refresh the embedded templates. Run `cargo run --bin ai-dlc-cli -- scaffold --provider claude` (or `--all`) to validate scaffold output locally. Format Rust code with `cargo fmt` and lint with `cargo clippy --all-targets -- -D warnings` before opening a PR. If you touch the Python test harness, run `uv sync --extra dev` followed by `uv run pytest tests/cli -q` to catch regressions.

## Coding Style & Naming Conventions
Follow standard Rust 2024 idioms: four-space indentation, `snake_case` for functions, and `PascalCase` for types and Clap subcommands. Keep CLI flags lowercase with hyphenated long names (`--provider`, `--all`). For templates and config assets, stick to lowercase directory names that match provider identifiers. Run `cargo fmt` (rustfmt) on every change set; avoid unchecked `unwrap()` unless the failure is impossible.

## Testing Guidelines
Prefer Rust unit or integration tests co-located with the CLI crate for new functionality, and gate new scaffolding logic with deterministic fixture checks. Maintain or retire the Python `pytest` suite intentionally—if you remove or regenerate templates, update the expected fixtures under `tests/cli/`. For manual verification, follow the README workflow: build, temporarily move `templates/`, run `./target/debug/ai-dlc-cli scaffold --all`, and confirm the regenerated tree matches expectations.

## Commit & Pull Request Guidelines
Commit history favors conventional prefixes (`feat:`, `refactor:`, `clean:`); continue that style and keep messages in the imperative mood. Each PR should describe the motivation, summarize functional changes, and link any relevant design notes or issues. Include before/after CLI output or directory listings when altering scaffolding results, note any template migrations, and call out follow-up work that remains.
