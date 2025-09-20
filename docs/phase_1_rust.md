# Phase 1 Implementation Plan: Standalone Scaffolding CLI

## 1. Objective

The goal of Phase 1 is to produce a single, self-contained, cross-platform binary, `ai-dlc`, built in Rust. This tool's primary function will be to scaffold new projects with best-practice templates for various AI providers. It must be easy to distribute and use, with no external dependencies for the end-user.

## 2. Core Technologies

*   **Language:** Rust (2021 Edition)
*   **Project Structure:** Cargo Workspace
*   **CLI Framework:** `clap` (with the `derive` feature) for robust argument parsing.
*   **Asset Bundling:** `include_dir` for embedding the template files directly into the binary.
*   **Error Handling:** `anyhow` for ergonomic and user-friendly error reporting.
*   **Logging:** `tracing` and `tracing-subscriber` for structured, context-aware logging.
*   **Testing:** The built-in Rust test framework, supplemented with `assert_fs` or `tempfile` for integration tests that touch the filesystem.

## 3. Repository & Crate Structure

We will use a Cargo workspace from the beginning to facilitate the addition of the server and worker crates in Phase 2.

```
/ai-dlc
├── .gitignore
├── Cargo.toml         # Defines the workspace
├── README.md
├── docs/
│   └── phase_1_rust.md
├── templates/         # Source location for templates to be embedded
│   ├── claude/
│   └── gemini/
└── crates/
    └── ai-dlc-cli/    # The first crate for our CLI tool
        ├── Cargo.toml
        └── src/
            └── main.rs
```

## 4. Detailed Task Breakdown

### Task 1: Initialize Cargo Workspace & CLI Crate

1.  Create the root directory `ai-dlc`.
2.  Inside, create the workspace `Cargo.toml`.
3.  Create the `crates/ai-dlc-cli` crate using `cargo new`.
4.  Set up the initial `.gitignore`.

### Task 2: Define the CLI Interface

1.  Add `clap` with the `derive` feature to the `ai-dlc-cli` dependencies.
2.  In `main.rs`, define the CLI structure using `clap`'s derive macros. This will include:
    *   A top-level `Cli` struct.
    *   A `Commands` enum, with a `Scaffold` variant.
    *   A `ScaffoldArgs` struct containing options like `--provider` (multiple) and `--all`.

### Task 3: Implement Asset Bundling

1.  Create the `templates` directory at the workspace root.
2.  Populate it with placeholder directories and files (e.g., `templates/gemini/agents/example.md`).
3.  Add the `include_dir` crate as a dependency.
4.  In the `scaffold` command's implementation, use `include_dir!` to embed the `templates` directory. The path will be relative, likely `include_dir!("$CARGO_MANIFEST_DIR/../../templates")`.

### Task 4: Implement Scaffolding Logic

1.  Write the core logic that processes the user's arguments (e.g., which providers were selected).
2.  Iterate through the embedded directory provided by `include_dir`.
3.  For each file, check if its path corresponds to a selected provider.
4.  Create the necessary directories on the user's local filesystem.
5.  Write the content of each embedded file to its corresponding new file on the filesystem.
6.  Implement logging using `tracing` to inform the user of the progress (e.g., "Creating `templates/gemini/agents/example.md`...").

### Task 5: Add Robust Error Handling

1.  Add the `anyhow` crate.
2.  Change the return type of `main` and other fallible functions to `anyhow::Result<()>`.
3.  Use the `?` operator on all I/O operations and other fallible calls to propagate errors cleanly. This will provide clear error messages to the user if something goes wrong (e.g., "Error: Permission denied while trying to create directory 'templates'").

### Task 6: Write Integration Tests

1.  Create an `tests` directory within `crates/ai-dlc-cli`.
2.  Add `assert_fs` or `tempfile` as a dev-dependency.
3.  Write an integration test that:
    a. Creates a temporary directory.
    b. Programmatically calls the `scaffold` command to run against that directory.
    c. Asserts that the expected files and directories were created correctly.
    d. Asserts that the file contents are correct.
    e. The temporary directory is automatically cleaned up on drop.

### Task 7: Documentation and Finalization

1.  Add doc comments (`///`) to all public functions, structs, and modules in the code.
2.  Create a `README.md` for the `ai-dlc-cli` crate.
3.  Run `cargo fmt` and `cargo clippy` to ensure code quality and style.
