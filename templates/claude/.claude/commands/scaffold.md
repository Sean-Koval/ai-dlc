# Command: /dlc:scaffold

## Description
Intelligent project and component scaffolding with AI-enhanced templates and best practices.

## Usage
```bash
/dlc:scaffold --template [template-type] --provider [ai-provider] [project-name]
```

## Options
- `--template`: Project template type (rust-cli, rust-api, python-api, typescript-api)
- `--provider`: AI provider integration (claude, gemini, roo)
- `--with-agents`: Include pre-configured AI agents
- `--enterprise`: Use enterprise-grade template with extensive tooling
- `--validate`: Run validation checks after scaffolding

## Workflow Steps

### 1. Project Analysis
- Detect existing project structure if any
- Analyze technology stack requirements
- Identify integration points

### 2. Template Selection
- Choose appropriate base template
- Apply provider-specific configurations
- Customize based on project requirements

### 3. Project Creation
- Create directory structure following best practices
- Generate configuration files (Cargo.toml, package.json, etc.)
- Set up version control with proper .gitignore
- Initialize dependency management

### 4. Development Environment
- Configure development tools (linting, formatting)
- Set up testing framework
- Create CI/CD pipeline templates
- Add pre-commit hooks

### 5. AI Integration
- Add CLAUDE.md with project context
- Configure AI agents for the technology stack
- Set up slash commands relevant to project type
- Create workflow automation hooks

### 6. Documentation
- Generate README.md with project overview
- Create CONTRIBUTING.md for team collaboration
- Add LICENSE file
- Set up documentation structure

### 7. Validation
- Verify all files created successfully
- Run initial build/compile to ensure setup is correct
- Execute test suite template
- Check for common configuration issues

## Examples

```bash
# Basic Rust CLI project
/dlc:scaffold --template rust-cli my-cli-tool

# Enterprise Rust API with Claude integration
/dlc:scaffold --template rust-api --provider claude --enterprise --with-agents my-api

# Python project with validation
/dlc:scaffold --template python-api --validate my-service
```

## Agent Collaboration
- **Template Designer**: Customizes templates for specific needs
- **DevOps Architect**: Sets up CI/CD and deployment configurations  
- **Rust/Python/TypeScript Expert**: Language-specific optimizations
- **Quality Engineer**: Ensures testing and quality gates are in place

## Success Metrics
- Project setup time: < 2 minutes
- All quality checks pass on initial setup
- Development environment fully functional
- Team can start development immediately

## Related Commands
- `/dlc:init` - Initialize existing project with AI enhancements
- `/dlc:validate` - Validate project structure and configuration
- `/dlc:implement` - Add features to scaffolded project