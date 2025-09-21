# ai-dlc-cli

`ai-dlc-cli` is the Rust command-line interface for the AI Development Lifecycle (AI-DLC) toolkit. It bundles best-practice project templates for supported AI providers and exposes commands that scaffold those templates onto a local filesystem.

## Installation

### From crates.io

```bash
cargo install ai-dlc-cli --locked
```

### From a local checkout

```bash
cargo install --path . --locked
```

Ensure `~/.cargo/bin` (or the installation directory configured for Cargo) is on your `PATH` so the `ai-dlc-cli` executable is discoverable.

## Usage

```bash
# Scaffold templates for a single provider
ai-dlc-cli scaffold --provider claude

# Scaffold templates for all known providers
ai-dlc-cli scaffold --all
```

The CLI embeds its template assets at compile time. Run `scripts/sync-cli-templates.sh` from the repository root before packaging to keep the embedded copies in sync with the canonical `templates/` directory.

## License

ai-dlc-cli is released under the MIT License. See [LICENSE](LICENSE) for details.
