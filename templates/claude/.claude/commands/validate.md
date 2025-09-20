# Command: /dlc:validate

## Description
Multi-dimensional code and architecture validation with quality gates and compliance checking.

## Usage
```bash
/dlc:validate [options] [target]
```

## Options
- `--mode`: Validation mode (comprehensive|targeted)
- `--security`: Security validation and vulnerability scanning
- `--performance`: Performance analysis and optimization opportunities
- `--architecture`: Architecture compliance and patterns
- `--quality`: Code quality metrics and standards
- `--dependencies`: Dependency validation and updates
- `--review`: Comprehensive code review
- `--fix`: Attempt to auto-fix issues

## Validation Modes

### Comprehensive Mode
Runs ALL validation checks in parallel for complete analysis:
- Code quality and formatting
- Security vulnerability scanning
- Performance profiling
- Architecture compliance
- Dependency auditing
- Documentation coverage
- Test coverage analysis
- Accessibility compliance (if applicable)

### Targeted Mode
Selective validation for specific concerns:
- Faster execution
- Resource-efficient
- Focused reporting
- Actionable insights

## Workflow Steps

### 1. Pre-Validation Setup
- Ensure project builds successfully
- Check for required tools
- Load validation configurations
- Prepare validation environment

### 2. Code Quality Validation
- **Formatting**: Check code formatting standards
- **Linting**: Run language-specific linters
- **Complexity**: Analyze cyclomatic complexity
- **Duplication**: Detect code duplication
- **Standards**: Verify coding standards compliance

### 3. Security Validation
- **Dependencies**: Scan for known vulnerabilities
- **Code Analysis**: Static security testing (SAST)
- **Secrets**: Check for exposed credentials
- **Permissions**: Validate file permissions
- **Input Validation**: Check for injection vulnerabilities

### 4. Performance Validation
- **Complexity Analysis**: Big O complexity checks
- **Memory Patterns**: Memory usage analysis
- **Query Optimization**: Database query review
- **Bundle Size**: Asset size optimization
- **Bottlenecks**: Performance hotspot detection

### 5. Architecture Validation
- **Pattern Compliance**: Design pattern verification
- **Dependency Rules**: Validate dependency directions
- **Module Boundaries**: Check module isolation
- **API Contracts**: Validate interface compliance
- **Documentation**: Architecture documentation coverage

### 6. Results and Reporting
- Generate detailed reports (HTML/JSON/Markdown)
- Prioritize issues by severity
- Provide fix recommendations
- Track validation history
- Generate compliance certificates

## Validation Rules

### Critical (Must Fix)
- Security vulnerabilities (High/Critical)
- Broken tests
- Build failures
- License violations
- Exposed secrets

### Important (Should Fix)
- Code quality issues
- Performance problems
- Missing documentation
- Low test coverage
- Technical debt

### Recommended (Nice to Fix)
- Style inconsistencies
- Minor optimizations
- Documentation improvements
- Refactoring opportunities

## Examples

```bash
# Comprehensive validation
/dlc:validate --mode comprehensive

# Security-focused validation
/dlc:validate --mode targeted --security --fix

# Pre-commit validation
/dlc:validate --quality --security --performance

# Architecture compliance check
/dlc:validate --architecture --dependencies

# Full review with auto-fix
/dlc:validate --review --fix

# CI/CD pipeline validation
/dlc:validate --mode comprehensive --output json > validation-report.json
```

## Quality Gates Configuration

```yaml
# .dlc/quality-gates.yml
quality_gates:
  security:
    vulnerabilities: 0  # No high/critical vulnerabilities
    secrets: 0         # No exposed secrets

  quality:
    coverage: 80       # Minimum test coverage
    complexity: 10     # Maximum cyclomatic complexity
    duplication: 5     # Maximum duplication percentage

  performance:
    build_time: 60s    # Maximum build time
    bundle_size: 5MB   # Maximum bundle size

  compliance:
    license: ["MIT", "Apache-2.0", "BSD"]
    documentation: 90  # Documentation coverage
```

## Agent Collaboration
- **Quality Engineer**: Code quality standards and metrics
- **Security Engineer**: Security validation and remediation
- **Performance Engineer**: Performance analysis and optimization
- **System Architect**: Architecture compliance and patterns

## Integration Points

### Pre-Commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
/dlc:validate --mode targeted --quality --security || exit 1
```

### CI/CD Pipeline
```yaml
# .github/workflows/validation.yml
- name: Run Validation
  run: |
    /dlc:validate --mode comprehensive --output json
```

## Success Metrics
- Zero critical issues
- < 5 important issues
- All quality gates passing
- Validation time < 2 minutes
- 100% compliance with standards

## Related Commands
- `/dlc:test` - Test execution and coverage
- `/dlc:analyze` - Deep code analysis
- `/dlc:audit` - Security and compliance auditing