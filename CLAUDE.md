# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Build the CLI from source
cargo build

# Build for release
cargo build --release

# Run the CLI (after building)
./target/debug/ai-dlc-cli

# Code quality checks
cargo fmt
cargo clippy
```

## Testing Commands

```bash
# Run all tests
cargo test

# Run tests for the CLI crate specifically
cargo test -p ai-dlc-cli
```

## CLI Usage

The `ai-dlc-cli` tool scaffolds AI development templates:

```bash
# Scaffold templates for specific provider(s)
./target/debug/ai-dlc-cli scaffold --provider gemini
./target/debug/ai-dlc-cli scaffold --provider claude --provider roo

# Scaffold templates for all supported providers
./target/debug/ai-dlc-cli scaffold --all
```

## Architecture Overview

This is a **Rust-based AI Development Lifecycle (AI-DLC) CLI tool** that helps development teams set up comprehensive AI-assisted development environments. The tool provides scaffolding templates that developers extract into their projects to enhance their coding experience with tools like Claude Code, Cursor, and other AI development environments.

### Core Purpose

**AI-DLC CLI is a template distribution tool, NOT a development assistant.** It provides:

1. **Template Distribution**: Extracts pre-configured AI agent definitions, slash commands, and workflows
2. **Environment Setup**: Helps teams establish consistent AI-assisted development practices
3. **Best Practices**: Delivers proven patterns for AI-enhanced development workflows

**The templates are used BY developers IN their projects, not by the AI-DLC tool itself.**

### Key Architectural Decisions

- **Cargo Workspace Structure**: Uses a workspace to prepare for future expansion (Phase 2 will add server/worker components)
- **Embedded Templates**: Templates are bundled directly into the binary using `include_dir` for zero-dependency distribution
- **Self-Contained Binary**: The CLI embeds all templates at compile time, making it fully portable
- **Provider-Agnostic**: Templates are organized by AI provider (Claude Code, Gemini, etc.) but the CLI itself is provider-neutral

### Codebase Structure

- **`/crates/ai-dlc-cli/`**: Main CLI application source code (the distribution tool)
- **`/templates/`**: Template content that gets embedded and distributed to user projects
  - **`/templates/claude/`**: Claude Code environment templates (agents, commands, workflows)
  - **`/templates/gemini/`**: Gemini-specific development environment templates
  - **`/templates/roo/`**: Roo platform templates
- **`/docs/`**: Project documentation and implementation plans
- **Workspace root**: Contains workspace-level configuration and documentation

### Template System Architecture

```
AI-DLC CLI Tool (Rust Binary)
├── Embeds templates at compile time
├── Distributes templates to user projects
└── Provides scaffolding commands

User Project (After Scaffolding)
├── .claude/ (or .gemini/, .roo/)
│   ├── agents/           # AI assistant definitions for Claude Code
│   ├── commands/         # Slash commands for Claude Code sessions
│   ├── workflows/        # Development workflow templates
│   └── hooks/           # Quality automation scripts
└── CLAUDE.md            # Project context for AI assistants
```

The CLI uses `include_dir!` to embed the entire `templates/` directory at compile time. The scaffold command extracts these embedded files to the user's local filesystem, creating provider-specific directory structures that enhance their AI development environment.

### Template Content Guidelines

**IMPORTANT**: When working on template content (`/templates/` directory), remember:

1. **Templates are for end-users, not this tool**: Agent definitions and commands in templates are designed to help developers with their coding tasks, NOT to help with AI-DLC CLI development
2. **Focus on development problems**: Template agents should solve common development challenges (debugging, testing, code review, architecture) rather than CLI tool issues
3. **Provider-specific optimization**: Templates should leverage the specific capabilities of each AI provider (Claude Code's slash commands, Gemini's features, etc.)
4. **Team collaboration**: Templates should facilitate team workflows, knowledge sharing, and consistent practices

**Example Template Agent Focus**:
- ✅ `@rust-architect`: Helps with Rust code optimization, memory safety, performance
- ✅ `@security-engineer`: Reviews code for vulnerabilities, suggests security improvements
- ❌ `@ai-dlc-helper`: Helps with using the AI-DLC CLI tool (this is meta and not useful)

### Dependencies

- **clap**: CLI argument parsing with derive macros
- **include_dir**: Compile-time directory embedding
- **anyhow**: Ergonomic error handling
- **tracing**: Structured logging
- **tokio**: Async runtime (full features)

## Testing the Template Embedding

To properly test that templates are correctly embedded and extracted:

1. Ensure `templates/` directory exists with desired structure
2. Run `cargo build` to embed templates into binary
3. **Delete** the source `templates/` directory: `rm -rf templates`
4. Run the binary: `./target/debug/ai-dlc-cli scaffold --all`
5. Verify templates are recreated correctly: `ls -R templates`

This workflow ensures the binary can recreate templates from embedded assets, not local files.

## Complete User Workflow

Understanding how teams use AI-DLC helps clarify the distinction between tool and templates:

### Step 1: Team Lead Sets Up Templates
```bash
# Team lead installs AI-DLC CLI and extracts templates
cargo build --release
./target/debug/ai-dlc-cli scaffold --provider claude
```

### Step 2: Developers Use Templates in Their IDE/Environment
```bash
# Developers use Claude Code with extracted templates
# These commands run IN Claude Code, not in AI-DLC CLI:
/dlc:generate --type module user_service
@rust-architect help optimize this function
/dlc:validate --comprehensive
```

### Step 3: Templates Enhance Development Experience
- **AI Agents** help with code review, architecture, security
- **Slash Commands** automate testing, validation, deployment
- **Workflows** guide TDD, feature development, team collaboration
- **Quality Gates** ensure consistent standards

**Key Point**: AI-DLC CLI runs once to set up templates. Templates run continuously to enhance development.

## Future Development

The project is planned to evolve through multiple phases:
- **Phase 1** (Current): Standalone scaffolding CLI for template distribution
- **Phase 2**: Local-first integrated system with Docker and Redis for team coordination
- **Phase 3**: Cloud deployment for enterprise team collaboration and template sharing