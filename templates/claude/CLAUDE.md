# Project Overview

[Brief description of your project, its goals, and key architectural decisions]

## Build and Development Commands

```bash
# Build the project
cargo build
cargo build --release

# Run tests
cargo test
cargo test --integration

# Code quality
cargo fmt
cargo clippy -- -D warnings

# Run the application
cargo run -- [arguments]
```

## Testing Instructions

```bash
# Unit tests
cargo test --lib

# Integration tests
cargo test --test '*'

# Coverage report
cargo tarpaulin --out Html

# Benchmark tests
cargo bench
```

## Code Style Guidelines

- Use idiomatic Rust patterns and follow the Rust API Guidelines
- Prefer explicit error handling with Result types over panics
- Use descriptive variable and function names
- Keep functions focused and under 50 lines when possible
- Document all public APIs with rustdoc comments
- Follow the existing project structure and patterns

## Key Files and Architecture

### Project Structure
```
src/
├── main.rs           # Application entry point
├── lib.rs           # Library exports
├── commands/        # CLI command implementations
├── agents/          # AI agent integrations
├── templates/       # Template management
└── utils/           # Utility functions
```

### Core Components
- **CLI Framework**: Clap for argument parsing with derive macros
- **Template Engine**: Include_dir for embedded templates
- **Error Handling**: Anyhow for ergonomic error management
- **Async Runtime**: Tokio for asynchronous operations
- **Logging**: Tracing for structured logging

## Environment Setup

### Required Tools
- Rust 1.75+ (check with `rustc --version`)
- Cargo (included with Rust)
- Git for version control

### Environment Variables
```bash
# Development
RUST_LOG=debug        # Enable debug logging
RUST_BACKTRACE=1     # Enable backtraces

# Production
RUST_LOG=info        # Production logging level
```

## Development Workflow

### Feature Development
1. Create feature branch from main
2. Implement with TDD approach
3. Run quality checks before commit
4. Create pull request with comprehensive description

### Quality Gates
Before committing:
- `cargo fmt --check` - Code formatting
- `cargo clippy` - Linting
- `cargo test` - All tests pass
- `cargo audit` - No security vulnerabilities

## AI Assistant Context

### Project Goals
- Provide comprehensive AI development lifecycle templates
- Support multiple AI providers (Claude, Gemini, Roo)
- Enable rapid project scaffolding with best practices
- Integrate AI-assisted development workflows

### Key Design Decisions
- **Embedded Templates**: Templates bundled in binary for portability
- **Workspace Structure**: Prepared for future expansion
- **Provider Agnostic**: Support multiple AI platforms
- **Zero Dependencies**: Self-contained CLI tool

### Current Implementation Phase
Phase 1: Standalone CLI tool for template scaffolding

## Common Tasks

### Adding a New Template
1. Create template files in `templates/[provider]/`
2. Rebuild to embed new templates
3. Test extraction with `cargo run -- scaffold --provider [provider]`

### Adding a New Command
1. Create command module in `src/commands/`
2. Add to command enum in `src/cli.rs`
3. Implement command logic
4. Add tests and documentation

### Debugging
- Enable debug logging: `RUST_LOG=debug cargo run`
- Use `dbg!()` macro for quick debugging
- Run specific test: `cargo test test_name -- --nocapture`

## Security Considerations

- Never commit credentials or secrets
- Validate all user inputs
- Use secure defaults for configurations
- Keep dependencies updated with `cargo update`
- Regular security audits with `cargo audit`

## Performance Guidelines

- Profile before optimizing
- Prefer iterators over collecting when possible
- Use appropriate data structures (HashMap vs BTreeMap)
- Consider memory usage for embedded templates
- Benchmark critical paths

## Documentation Standards

- Update this file when adding major features
- Document all public APIs with examples
- Keep README.md current with usage instructions
- Add inline comments for complex logic
- Create ADRs for significant decisions