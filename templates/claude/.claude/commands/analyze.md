# Command: /dlc:analyze

## Description
Multi-perspective codebase and architecture analysis with AI-powered insights and recommendations.

## Usage
```bash
/dlc:analyze [options] [target]
```

## Options
- `--architecture`: Architecture patterns and structure analysis
- `--tech-debt`: Technical debt assessment and prioritization
- `--performance`: Performance bottlenecks and optimization opportunities
- `--security`: Security patterns and vulnerability analysis
- `--complexity`: Code complexity and maintainability metrics
- `--dependencies`: Dependency analysis and optimization
- `--recommendations`: Generate improvement recommendations
- `--visualize`: Create visual representations of analysis

## Analysis Perspectives

### Architecture Analysis
- **Structure**: Module organization and boundaries
- **Patterns**: Design pattern usage and consistency
- **Coupling**: Component coupling and cohesion metrics
- **Layers**: Layer separation and dependency direction
- **Interfaces**: API design and contract analysis

### Technical Debt Analysis
- **Code Smells**: Identify problematic code patterns
- **Duplication**: Find and measure code duplication
- **Complexity**: Locate overly complex code
- **Outdated**: Find deprecated or outdated patterns
- **Refactoring**: Prioritize refactoring opportunities

### Performance Analysis
- **Algorithms**: Analyze algorithmic complexity
- **Memory**: Memory usage patterns and leaks
- **I/O**: I/O operations and optimization
- **Concurrency**: Thread safety and parallel efficiency
- **Caching**: Cache usage and opportunities

### Dependency Analysis
- **Graph**: Visualize dependency relationships
- **Cycles**: Detect circular dependencies
- **Updates**: Identify outdated dependencies
- **Security**: Known vulnerabilities in dependencies
- **Optimization**: Unnecessary or duplicate dependencies

## Workflow Steps

### 1. Codebase Scanning
- Parse project structure
- Build dependency graph
- Extract metrics and patterns
- Identify key components

### 2. Pattern Recognition
- Detect design patterns in use
- Find anti-patterns
- Identify architectural styles
- Recognize framework patterns

### 3. Metrics Collection
- **Size Metrics**: LOC, files, modules
- **Complexity Metrics**: Cyclomatic, cognitive
- **Coupling Metrics**: Afferent, efferent coupling
- **Quality Metrics**: Test coverage, documentation

### 4. Issue Detection
- Performance bottlenecks
- Security vulnerabilities
- Maintainability issues
- Scalability concerns

### 5. Recommendation Generation
- Prioritized improvement list
- Refactoring suggestions
- Optimization opportunities
- Architecture improvements

### 6. Visualization
- Dependency graphs
- Complexity heat maps
- Architecture diagrams
- Trend charts

## Analysis Reports

### Architecture Report
```markdown
## Architecture Analysis

### Structure
- Modules: 12
- Layers: 3 (presentation, business, data)
- Components: 45

### Patterns Detected
- Repository Pattern (data layer)
- Factory Pattern (object creation)
- Observer Pattern (event handling)

### Issues
- Circular dependency: module A ↔ module B
- Layer violation: presentation → data

### Recommendations
1. Break circular dependency using interface
2. Introduce service layer for data access
```

### Technical Debt Report
```markdown
## Technical Debt Analysis

### High Priority
- Complex function: parse_config (complexity: 25)
- Duplicate code: 15% in authentication module
- Deprecated API usage: 3 instances

### Medium Priority
- Missing tests: 5 critical paths
- Incomplete documentation: 30% of public APIs

### Estimated Effort
- Total: 40 hours
- High Priority: 20 hours
- Medium Priority: 20 hours
```

## Examples

```bash
# Comprehensive architecture analysis
/dlc:analyze --architecture --visualize

# Technical debt assessment
/dlc:analyze --tech-debt --recommendations

# Performance bottleneck analysis
/dlc:analyze --performance --complexity src/

# Dependency security scan
/dlc:analyze --dependencies --security

# Full analysis with visualizations
/dlc:analyze --architecture --tech-debt --performance --visualize

# Generate improvement roadmap
/dlc:analyze --recommendations --output roadmap.md
```

## Visualization Outputs

### Dependency Graph
```
┌─────────┐     ┌─────────┐
│   CLI   │────▶│  Core   │
└─────────┘     └─────────┘
     │               │
     ▼               ▼
┌─────────┐     ┌─────────┐
│Commands │     │ Utils   │
└─────────┘     └─────────┘
```

### Complexity Heatmap
```
src/
├── main.rs          [██░░░] Low
├── parser.rs        [████░] High
├── validator.rs     [███░░] Medium
└── utils.rs         [█░░░░] Low
```

## Agent Collaboration
- **System Architect**: Architecture patterns and design
- **Performance Engineer**: Performance analysis and optimization
- **Technical Debt Analyst**: Debt identification and prioritization
- **Security Engineer**: Security pattern analysis

## Thresholds and Metrics

### Complexity Thresholds
- **Low**: < 5
- **Medium**: 5-10
- **High**: 10-20
- **Very High**: > 20

### Coupling Thresholds
- **Low Coupling**: < 5 dependencies
- **Medium Coupling**: 5-10 dependencies
- **High Coupling**: > 10 dependencies

### Code Duplication
- **Acceptable**: < 3%
- **Warning**: 3-5%
- **Critical**: > 5%

## Success Metrics
- No critical architecture violations
- Technical debt < 10% of codebase
- All performance bottlenecks identified
- Clear improvement roadmap generated
- Visualizations aid understanding

## Related Commands
- `/dlc:validate` - Validation and quality checks
- `/dlc:refactor` - Apply recommended improvements
- `/dlc:evolve` - Long-term architecture evolution