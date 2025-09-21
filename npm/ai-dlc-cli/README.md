# ai-dlc-cli (npm wrapper)

This package exposes the `ai-dlc-cli` Rust binary to Node.js environments. Installing it with npm downloads and caches the compiled CLI via `cargo install`, allowing you to run the AI Development Lifecycle scaffolding commands with `npx ai-dlc` or a global `ai-dlc-cli` binary.

## Install

```bash
npm install -g ai-dlc-cli
# or
npx ai-dlc scaffold --all
```

A Rust toolchain must be available on the machine that runs the npm install step.

## Repository

Development happens in the main AI-DLC repository: <https://github.com/antlor/ai-dlc>

## License

MIT
