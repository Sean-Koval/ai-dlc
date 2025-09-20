# Command: /dlc:test

## Description
Comprehensive testing workflow orchestration with AI-powered test generation and coverage analysis.

## Usage
```bash
/dlc:test [options] [target]
```

## Options
- `--generate`: Generate test cases automatically
- `--coverage`: Run with coverage analysis (specify target %)
- `--unit`: Run only unit tests
- `--integration`: Run integration tests
- `--e2e`: Run end-to-end tests
- `--performance`: Run performance benchmarks
- `--tdd-cycle`: Interactive TDD workflow
- `--ai-powered`: Use AI for test case generation
- `--fix-failing`: Attempt to fix failing tests

## Workflow Steps

### 1. Test Discovery
- Scan codebase for existing tests
- Identify untested code paths
- Analyze test coverage gaps
- Prioritize testing needs

### 2. Test Generation (if --generate)
- Analyze function signatures and types
- Generate positive test cases
- Create negative/edge test cases
- Build integration test scenarios
- Generate property-based tests where applicable

### 3. Test Execution
- Run tests in parallel where possible
- Capture detailed output and timing
- Track flaky test patterns
- Monitor resource usage during tests

### 4. Coverage Analysis
- Calculate line coverage
- Identify branch coverage
- Find uncovered code paths
- Generate coverage reports (HTML/JSON)

### 5. Performance Testing (if --performance)
- Run benchmark suites
- Compare against baselines
- Identify performance regressions
- Generate performance reports

### 6. Result Analysis
- Summarize test results
- Highlight failures with context
- Suggest fixes for common issues
- Track test history and trends

## Test Categories

### Unit Tests
```bash
# Run all unit tests
/dlc:test --unit

# Generate unit tests for specific module
/dlc:test --generate --unit src/parser/

# Run with coverage target
/dlc:test --unit --coverage 90%
```

### Integration Tests
```bash
# Run integration test suite
/dlc:test --integration

# Generate integration tests
/dlc:test --generate --integration --ai-powered
```

### TDD Cycle
```bash
# Interactive TDD workflow
/dlc:test --tdd-cycle "new sorting algorithm"

# Workflow:
# 1. Write failing test
# 2. Run test (confirm failure)
# 3. Implement minimum code
# 4. Run test (confirm pass)
# 5. Refactor
# 6. Run test (confirm still passes)
```

## Test Generation Patterns

### Unit Test Template
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_function_positive_case() {
        // Arrange
        let input = prepare_input();

        // Act
        let result = function_under_test(input);

        // Assert
        assert_eq!(result, expected_value);
    }

    #[test]
    fn test_function_edge_case() {
        // Edge case testing
    }

    #[test]
    #[should_panic(expected = "error message")]
    fn test_function_error_case() {
        // Error case testing
    }
}
```

## Coverage Requirements

### Minimum Coverage Targets
- Unit tests: 80% line coverage
- Integration tests: 60% coverage
- Critical paths: 95% coverage
- New code: 90% coverage

## Examples

```bash
# Comprehensive test suite
/dlc:test --unit --integration --coverage 85%

# Generate tests with AI assistance
/dlc:test --generate --ai-powered src/

# Run TDD cycle for new feature
/dlc:test --tdd-cycle "user authentication"

# Performance regression testing
/dlc:test --performance --baseline main

# Fix failing tests automatically
/dlc:test --fix-failing --unit
```

## Agent Collaboration
- **Quality Engineer**: Test strategy and best practices
- **Test Automation Specialist**: Test generation and optimization
- **Performance Engineer**: Performance testing and analysis
- **Domain Expert**: Business logic validation

## Success Metrics
- All tests passing
- Coverage meets targets
- No performance regressions
- Test execution time < 5 minutes
- Zero flaky tests

## Related Commands
- `/dlc:implement` - Implementation with TDD
- `/dlc:validate` - Quality validation
- `/dlc:analyze` - Code analysis including testability