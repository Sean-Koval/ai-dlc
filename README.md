# AI-DLC (AI Development Lifecycle) Toolkit

This repository contains the source code for the `ai-dlc` toolkit, a command-line application designed to manage and streamline the lifecycle of AI-driven development. It provides a curated collection of templates, agent definitions, and a companion CLI to orchestrate agentic workflows.

This project is currently under active development and is being built using the **Rust** programming language for performance, reliability, and security.

## Current Status: Phase 1 - Standalone Scaffolding CLI

The current development focus is on **Phase 1**, which delivers a self-contained `ai-dlc` command-line tool. The primary feature of this phase is the `scaffold` command.

This command generates best-practice directory structures and template files for various AI providers (e.g., Claude, Gemini, Roo), allowing developers to quickly start new projects without needing to create boilerplate from scratch.

## Project Structure

*   `docs/`: Contains project planning and engineering documentation, such as the `phase_1_rust.md` implementation plan.
*   `templates/`: The source-of-truth for the standard templates that are bundled into the `ai-dlc` binary.
*   `crates/ai-dlc-cli/`: The source code for the main Rust CLI application.

## Getting Started

### Installation Options

#### Cargo (Rust tooling required)

```bash
# Install from the workspace while developing locally
cargo install --path crates/ai-dlc-cli --locked

# Once published, install directly from crates.io
cargo install ai-dlc-cli --locked
```

Cargo places binaries in `~/.cargo/bin`; ensure that directory is on your `PATH` so the `ai-dlc-cli` command is available globally.

#### npm (Node.js 18+ and Rust tooling required)

```bash
# Global install
npm install -g ai-dlc-cli

# On-demand execution
npx ai-dlc scaffold --all
```

The npm package wraps the Rust binary and runs `cargo install ai-dlc-cli` during `postinstall`. Make sure a Rust toolchain is available on the machine where you execute the npm commands.

### Usage

After installing via either method, you can invoke the CLI directly:

```bash
# Scaffold templates for a specific provider
ai-dlc-cli scaffold --provider gemini

# Scaffold templates for all supported providers
ai-dlc-cli scaffold --all

# The npm wrapper also exposes `ai-dlc` as an alias
ai-dlc scaffold --provider claude
```

If you prefer to build from source without installing, run `cargo build` and use `./target/debug/ai-dlc-cli` as before.

## Development & Testing

The `ai-dlc` tool embeds the standard templates directly into the final binary to make it self-contained. This requires a specific workflow to test the scaffolding functionality correctly.

To test that the binary can recreate the templates from its embedded assets, follow these steps:

1.  **Ensure Source Templates Exist:** Make sure the `templates/` directory at the root of this repository is populated with the desired file structure.

2.  **Sync Embedded Assets:** Run `scripts/sync-cli-templates.sh` to mirror the root `templates/` directory into the embedded copy that ships with the CLI.
    ```bash
    scripts/sync-cli-templates.sh
    ```

3.  **Build the Application:** Run `cargo build`. This process reads the embedded templates under `crates/ai-dlc-cli/embedded-templates/` and bundles them into the `ai-dlc-cli` binary.

4.  **Delete the Source Directory:** Before testing, you must delete the source `templates/` directory. This ensures your test is running against the embedded assets, not the local files.
    ```bash
    rm -rf templates
    ```

5.  **Run the Executable:** Execute the compiled binary to run the scaffold command.
    ```bash
    ./target/debug/ai-dlc-cli scaffold --all
    ```

6.  **Verify the Output:** Check that the `templates/` directory has been successfully recreated with the correct structure and content.
    ```bash
    ls -R templates
    ```

## Future Phases

This project is planned to evolve beyond the standalone CLI:

*   **Phase 2: The Local-First Integrated System:** Will introduce a local server, worker, and queue (using Docker and Redis) to enable full workflow orchestration on a developer's machine.
*   **Phase 3: Cloud & Multi-User Deployment:** Will involve deploying the server components to the cloud to support team-wide collaboration, central logging, and a single source of truth.
