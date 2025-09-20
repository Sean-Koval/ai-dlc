# Test-Driven Development (TDD) Workflow

## Overview
This workflow implements the Red-Green-Refactor cycle for test-driven development, ensuring high code quality and comprehensive test coverage.

## Workflow Steps

### 1. Red Phase - Write Failing Test
```bash
# Start TDD cycle
/dlc:test --tdd-cycle "feature description"
```

**Process:**
1. Understand the requirement clearly
2. Write the simplest possible test that exercises the new functionality
3. Ensure the test fails for the right reason
4. Verify test is well-named and clear

**Example Test Structure:**
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn should_parse_valid_template_config() {
        // Arrange
        let config_str = r#"
            name = "rust-cli"
            version = "1.0.0"
        "#;

        // Act
        let result = parse_template_config(config_str);

        // Assert
        assert!(result.is_ok());
        let config = result.unwrap();
        assert_eq!(config.name, "rust-cli");
        assert_eq!(config.version, "1.0.0");
    }
}
```

### 2. Green Phase - Make Test Pass
```bash
# Implement minimal code to pass test
/dlc:implement --minimal --test-focused
```

**Process:**
1. Write the simplest code that makes the test pass
2. Don't worry about elegance or efficiency yet
3. Focus only on making the test green
4. Run tests frequently to ensure progress

**Implementation Guidelines:**
- Use the simplest solution possible
- Hard-code values if necessary (will be refactored later)
- Don't implement more than what the test requires
- Ensure all existing tests still pass

### 3. Refactor Phase - Improve Design
```bash
# Refactor while maintaining test coverage
/dlc:refactor --maintain-tests --improve-design
```

**Process:**
1. Improve code structure and design
2. Remove duplication
3. Improve naming and clarity
4. Optimize performance if needed
5. Ensure all tests still pass

**Refactoring Checklist:**
- [ ] Remove code duplication
- [ ] Improve variable and function names
- [ ] Extract methods where appropriate
- [ ] Simplify complex expressions
- [ ] Add documentation comments
- [ ] Verify all tests still pass

## TDD Best Practices

### Test Naming Convention
```rust
// Pattern: should_[expected_behavior]_when_[condition]
#[test]
fn should_return_error_when_template_not_found() { }

#[test]
fn should_create_directory_structure_when_scaffolding_rust_project() { }

#[test]
fn should_validate_config_when_all_required_fields_present() { }
```

### Test Organization
```rust
// Group related tests in modules
mod template_parsing {
    use super::*;

    #[test]
    fn should_parse_valid_toml() { }

    #[test]
    fn should_reject_invalid_toml() { }
}

mod project_scaffolding {
    use super::*;

    #[test]
    fn should_create_rust_project_structure() { }

    #[test]
    fn should_create_cargo_toml_with_correct_metadata() { }
}
```

### Test Data Management
```rust
// Use test builders for complex objects
struct TestProjectBuilder {
    name: String,
    template: String,
    features: Vec<String>,
}

impl TestProjectBuilder {
    fn new() -> Self {
        Self {
            name: "test-project".to_string(),
            template: "rust-cli".to_string(),
            features: vec![],
        }
    }

    fn with_name(mut self, name: &str) -> Self {
        self.name = name.to_string();
        self
    }

    fn with_template(mut self, template: &str) -> Self {
        self.template = template.to_string();
        self
    }

    fn build(self) -> ProjectConfig {
        ProjectConfig {
            name: self.name,
            template: self.template,
            features: self.features,
        }
    }
}

// Usage in tests
#[test]
fn should_scaffold_project_with_custom_name() {
    let config = TestProjectBuilder::new()
        .with_name("my-awesome-project")
        .with_template("rust-api")
        .build();

    let result = scaffold_project(config);
    assert!(result.is_ok());
}
```

## TDD Cycle Commands

### Quick TDD Commands
```bash
# Start new TDD cycle
/dlc:test --tdd-cycle "user can upload files"

# Run tests in watch mode
/dlc:test --watch --unit

# Run specific test
/dlc:test --test "test_file_upload"

# Check coverage after implementation
/dlc:test --coverage --show-missing
```

### Integration with Git
```bash
# TDD workflow with git integration
git checkout -b feature/file-upload

# Red phase - commit failing test
/dlc:test --tdd-cycle "file upload validation"
git add tests/
git commit -m "Red: Add failing test for file upload validation"

# Green phase - commit minimal implementation
/dlc:implement --minimal --for-test "test_file_upload_validation"
git add src/
git commit -m "Green: Minimal implementation for file upload"

# Refactor phase - commit improvements
/dlc:refactor --target "file_upload_module" --maintain-tests
git add .
git commit -m "Refactor: Improve file upload implementation"
```

## Quality Gates in TDD

### Pre-commit TDD Checks
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Ensure no tests are skipped or ignored
if grep -r "#\[ignore\]" tests/ >/dev/null 2>&1; then
    echo "❌ Ignored tests found. Remove #[ignore] before committing."
    exit 1
fi

# Ensure test coverage hasn't decreased
current_coverage=$(cargo tarpaulin --quiet --output Json | jq '.coverage')
if [[ $(echo "$current_coverage < 80" | bc) -eq 1 ]]; then
    echo "❌ Test coverage below 80%: $current_coverage%"
    exit 1
fi

echo "✅ TDD quality checks passed"
```

### Continuous Testing
```yaml
# GitHub Actions workflow for TDD
name: TDD Workflow
on: [push, pull_request]

jobs:
  tdd:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable

      - name: Run TDD checks
        run: |
          # Ensure tests pass
          cargo test --verbose

          # Check coverage
          cargo install cargo-tarpaulin
          cargo tarpaulin --timeout 120 --fail-under 80

          # Ensure no ignored tests
          ! grep -r "#\[ignore\]" tests/
```

## Common TDD Patterns

### Testing Error Cases
```rust
#[test]
fn should_return_error_when_template_directory_missing() {
    let template_path = Path::new("nonexistent/template");

    let result = load_template(template_path);

    assert!(result.is_err());
    match result.unwrap_err() {
        TemplateError::NotFound(path) => {
            assert_eq!(path, template_path);
        }
        _ => panic!("Expected TemplateError::NotFound"),
    }
}
```

### Testing Async Code
```rust
#[tokio::test]
async fn should_download_template_from_remote_url() {
    let url = "https://example.com/templates/rust-cli.zip";

    let result = download_template(url).await;

    assert!(result.is_ok());
    let template = result.unwrap();
    assert!(!template.files.is_empty());
}
```

### Property-Based Testing
```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn project_name_validation_is_consistent(
        name in "[a-zA-Z][a-zA-Z0-9_-]{0,50}"
    ) {
        let result = validate_project_name(&name);
        prop_assert!(result.is_ok());
    }

    #[test]
    fn invalid_names_are_rejected(
        name in "[0-9].*|.*[^a-zA-Z0-9_-].*"
    ) {
        let result = validate_project_name(&name);
        prop_assert!(result.is_err());
    }
}
```

## TDD Workflow Integration

### With AI Agents
- **Quality Engineer**: Ensures test quality and coverage standards
- **Rust Architect**: Guides idiomatic test patterns and implementation
- **CLI Expert**: Validates command-line interface behavior through tests

### Success Metrics
- All tests pass in each phase
- Coverage increases with each feature
- Cycle time: Red → Green → Refactor < 15 minutes
- No ignored or skipped tests in main branch
- Clear, descriptive test names and structure

This TDD workflow ensures high-quality, well-tested code while maintaining development velocity and providing rapid feedback on implementation correctness.