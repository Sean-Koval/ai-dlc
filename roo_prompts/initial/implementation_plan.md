# AI-DLC Prompt Template Tool: Implementation Plan

## Introduction

This document outlines the implementation plan for the AI-DLC Prompt Template Tool, a CLI utility (`ai-dlc`) designed to standardize and accelerate the creation and management of `:PromptTemplate` artifacts within the `:AIDevelopmentLifecycle`. The tool provides a `:Solution` to the `:Problem` of inconsistent prompt creation, specifically addressing the needs of the Professional Services team (:UserRole) in the initial development `:Context` (Stage 0).

The plan is structured into iterative phases and subphases, suitable for the Orchestrator-driven workflow and immediate Code->Test->Fix **Boomerang Cycle** with a **Targeted Testing Strategy**.

## Implementation Phases

### Phase 0: Core Setup & Environment

This phase establishes the foundational environment and basic CLI structure.

#### Subphase 0.1: Project Initialization & Environment Management

*   **Description:** Set up the project structure and configure the Python environment.
*   **SAPPO Concepts:**
    *   `:Technology`: Python 3.13, uv
    *   `:ProjectManifest`: `pyproject.toml`
    *   `:DependencyIssues`: Mitigated by using `uv` and `uv.lock` for deterministic environments.
*   **TDD Anchor Points (Core Logic):**
    *   Verify that `uv` can successfully install dependencies listed in `pyproject.toml`.
    *   Verify that the correct Python version (:Technology:Python 3.12) is used within the `uv` environment.

#### Subphase 0.2: Basic CLI Structure

*   **Description:** Implement the main CLI entry point using Typer.
*   **SAPPO Concepts:**
    *   `:Technology`: Typer
    *   `:ArchitecturalPattern`: Command-Line Interface
*   **TDD Anchor Points (Core Logic):**
    *   Verify that the `ai-dlc` command can be executed without errors (e.g., `ai-dlc --help`).
    *   Verify that basic command structure is recognized by Typer.

### Phase 1: Scaffolding & Generation Basics

This phase implements the core functionality for creating new prompt libraries and generating prompts from templates.

#### Subphase 1.1: `scaffold` command

*   **Description:** Implement the `scaffold` command to create a predefined directory structure for a new prompt library/repository.
*   **SAPPO Concepts:**
    *   `:ComponentRole`: Scaffolding utility
    *   `:ArchitecturalPattern`: Directory Skeleton (implicit in the structure created)
*   **TDD Anchor Points (Core Logic):**
    *   Verify that `ai-dlc scaffold <team_name>` creates the expected root directory `<team_name>`.
    *   Verify that the command creates the necessary subdirectories (e.g., `templates/`, `schemas/`, `examples/`, `checks/`) within the team directory.
    *   Verify that placeholder files (e.g., `.gitkeep`, basic READMEs) are created in the scaffolded directories.

#### Subphase 1.2: `generate` command (Basic Templating)

*   **Description:** Implement the basic `generate` command to take a Jinja2 template file and render it. Initial implementation will not include input data or validation.
*   **SAPPO Concepts:**
    *   `:Technology`: Jinja2
    *   `:PromptTemplate`: Generation mechanism
*   **TDD Anchor Points (Core Logic):**
    *   Verify that `ai-dlc generate --template <template_file.md.j2>` reads the specified template.
    *   Verify that the command outputs the raw content of the template file without processing Jinja2 syntax.

### Phase 2: Input Validation

This phase integrates schema-driven validation for input data.

#### Subphase 2.1: Schema Definition & Loading

*   **Description:** Define the process for creating and loading JSON schema files (`.schema.json`).
*   **SAPPO Concepts:**
    *   `:Technology`: jsonschema
    *   `:ArchitecturalPattern`: :DataValidation (Schema-driven)
    *   `:Context`: Input data structure
*   **TDD Anchor Points (Core Logic):**
    *   Verify that a valid JSON schema file can be loaded successfully.
    *   Verify that an invalid JSON schema file (syntax error) is detected and reported.

#### Subphase 2.2: `generate` command Integration with Schema Validation

*   **Description:** Modify the `generate` command to accept an input YAML file and a schema file, validate the YAML against the schema using `jsonschema`, and then use the validated data to render the Jinja2 template.
*   **SAPPO Concepts:**
    *   `:Technology`: jsonschema, Jinja2
    *   `:ArchitecturalPattern`: :DataValidation, Templating Engine
    *   `:Problem`: Invalid input data leading to incorrect prompts.
    *   `:Solution`: Automated schema validation.
*   **TDD Anchor Points (Core Logic):**
    *   Verify that `ai-dlc generate --input <valid_input.yaml> --schema <schema.json> --template <template.md.j2>` successfully validates the input and renders the template using the input data.
    *   Verify that `ai-dlc generate --input <invalid_input.yaml> --schema <schema.json> --template <template.md.j2>` fails validation and reports specific schema errors.
    *   Verify that Jinja2 variables in the template are correctly replaced by data from the validated input YAML.
    *   **Contextual Integration Testing:** Verify integration between the `jsonschema` validation logic and the Jinja2 rendering process.

### Phase 3: Custom Prompt Validation

This phase adds support for custom, domain-specific validation rules for the generated prompts.

#### Subphase 3.1: Custom Check Rule Loading

*   **Description:** Define the structure for custom validation rules in `.CHECKS.yaml` files and implement logic to load these rules.
*   **SAPPO Concepts:**
    *   `:CustomValidationRule`
    *   `:ArchitecturalPattern`: Rule Engine (implicit)
*   **TDD Anchor Points (Core Logic):**
    *   Verify that a valid `.CHECKS.yaml` file can be loaded and parsed into a usable data structure.
    *   Verify that an invalid `.CHECKS.yaml` file (syntax error or incorrect structure) is detected and reported.

#### Subphase 3.2: `validate` command

*   **Description:** Implement the `validate` command to take a generated prompt file and a set of custom check rules, applying the rules to the prompt content.
*   **SAPPO Concepts:**
    *   `:CustomValidationRule`
    *   `:Problem`: Generated prompts not meeting specific domain requirements.
    *   `:Solution`: Automated custom validation.
*   **TDD Anchor Points (Core Logic):**
    *   Verify that `ai-dlc validate --prompt <generated_prompt.md> --checks <checks.CHECKS.yaml>` executes the checks.
    *   Verify that the command reports violations for prompts that fail specific custom rules.
    *   Verify that the command reports success for prompts that pass all custom rules.
    *   Verify different types of custom rules (e.g., regex match, keyword presence) are correctly applied.


## Development Approach & Testing

Development will follow an iterative, micro-task-based approach. Each subphase represents a set of micro-tasks to be implemented and tested.

The **Targeted Testing Strategy** will be applied in each **Boomerang Cycle**:

1.  **Core Logic Testing:** `@tester-core` will verify the internal correctness of the implemented unit (e.g., a specific command's parsing, validation function's output, redaction logic's transformation) using the **TDD Anchor Points** defined in each subphase. This includes testing base cases and edge cases.
2.  **Contextual Integration Testing:** Based on Orchestrator guidance, `@tester-core` will verify key interactions with immediate collaborators (e.g., `generate` command interacting with validation logic, `redact` command processing output from `generate`).

This ensures that each `:SoftwareComponent` is robust and integrates correctly within its immediate `:Context` before proceeding to broader integration.

## Conclusion

This plan provides a roadmap for implementing the core features of the AI-DLC Prompt Template Tool, addressing the identified `:Problem` for the Professional Services team (:UserRole) within the initial `:AIDevelopmentLifecycle` `:Context`. By following this phased approach and adhering to the **Targeted Testing Strategy**, we aim to deliver a robust and reliable tool.