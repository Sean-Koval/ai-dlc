# AI-DLC Prompt Template Tool: Empowering Efficient AI Development

## Introduction

The AI-DLC Prompt Template Tool is a robust CLI utility (`ai-dlc`) designed to standardize and accelerate the creation of `:PromptTemplate` artifacts within the `:AIDevelopmentLifecycle`. Its mission is to provide teams, starting with the Professional Services team (:UserRole), with capabilities for scaffolding, generating, and validating prompt templates, thereby accelerating AI project delivery.

The tool is built using Python (:Technology), leveraging `uv` (:Technology) for efficient and deterministic environment management, as defined in the `:ProjectManifest`.

## Core Problem Addressed

A significant `:Problem` in AI development is the challenge of consistently creating well-crafted prompts tailored to the specific needs of different teams and stages of the `:AIDevelopmentLifecycle` (such as research, design, and implementation). Inconsistent, ad-hoc prompt creation leads to inefficiencies, variable quality in LLM interactions, and difficulties in maintaining and reusing prompts across projects. While LLMs are powerful, the output they generate often requires human validation for key pieces, highlighting the need for a structured approach to prompt engineering that facilitates this review process.

The AI-DLC Prompt Template Tool provides a `:Solution` by enabling teams to scaffold a new prompt library/repository, promoting standardization, reusability, and validation of `:PromptTemplate`s. This tool (representing Stage 0 of the AI-DLC project, focused on prompts) ensures a more structured and reliable approach to prompt engineering that supports the creation of high-quality, context-aware prompts while acknowledging the critical role of human oversight.

## Key Features & Technologies

The `ai-dlc` tool incorporates several key features and leverages specific technologies to achieve its goals:

*   **CLI Interface (`ai-dlc`):** Built with Typer (:Technology), providing an intuitive command-line interface with distinct sub-commands for different operations (e.g., `scaffold`, `generate`, `validate`, `redact`).
*   **Templating Engine:** Utilizes Jinja2 (:Technology) as a powerful templating engine. This allows for the creation of dynamic and reusable `:PromptTemplate` files, stored typically as `.md.j2` files (e.g., [`templates/research/idea_generation.md.j2`](templates/research/idea_generation.md.j2)).
*   **Schema-Driven Inputs:** Employs `jsonschema` (:Technology) to implement a `:DataValidation` :ArchitecturalPattern. This ensures data integrity by validating user-defined input YAML files (e.g., `schemas/team_input.schema.json`) against predefined JSON schemas before they are used for prompt generation.
*   **Custom Prompt Validation:** Supports the definition of domain-specific `:CustomValidationRule`s through `checks/*.CHECKS.yaml` files, allowing for validation of generated prompts beyond basic schema checks.
*   **Security by Design:** Includes a `:DataRedaction` utility (P5-A) as a crucial `:SecurityFeature`. This addresses the `:SecurityVulnerability` :Problem of potential leakage of sensitive information, such as PII or secrets (e.g., emails, API tokens), into LLMs by redacting specified patterns from generated prompts.
*   **Deterministic Environments:** Uses `uv` (:Technology) for managing Python version (`3.12`) and project dependencies. The `uv.lock` file ensures reproducible builds across different environments, mitigating `:DependencyIssues` related to package versions.

## High-Level Workflow

The typical workflow using the `ai-dlc` tool involves the following steps:

1.  **Define Inputs:** Users define team-specific input data in a YAML file (e.g., `examples/professional_services.yaml`).
2.  **Validate Inputs:** The input YAML file is validated against a corresponding JSON schema (e.g., `schemas/team_input.schema.json`) using the schema-driven validation `:ArchitecturalPattern`.
3.  **Author Templates:** Prompt engineers author reusable Jinja2 templates for various prompt categories (e.g., idea generation, user stories).
4.  **Generate Prompts:** The `ai-dlc generate` command combines the validated input YAML with the chosen Jinja2 template(s) to produce the final prompt text.
5.  **Validate Prompts:** The `ai-dlc validate --prompts <dir>` command is used to check the generated prompts against defined `:CustomValidationRule`s in `checks/*.CHECKS.yaml` files.
6.  **Redact Sensitive Data (Optional but Recommended):** The `:DataRedaction` utility can be applied to generated prompts to remove sensitive information.
7.  The [`examples/professional_services.yaml`](examples/professional_services.yaml) file serves as a `:GoldenPath` example, demonstrating a typical input structure.

## Benefits for the Professional Services Team

Adopting the AI-DLC Prompt Template Tool offers several key benefits for the Professional Services team:

*   **Faster Onboarding:** Provides a standardized process and toolset, accelerating the onboarding of team members to new AI projects.
*   **Consistent Quality:** Ensures consistent quality in both client-facing and internal AI-generated content through standardized templates and validation.
*   **Reduced Errors:** Minimizes errors through automated input validation (`:DataValidation`) and custom prompt validation (`:CustomValidationRule`s).
*   **Easier Collaboration:** Facilitates easier collaboration among team members on prompt engineering efforts by providing a shared framework and artifact structure.

## Development Approach

The `ai-dlc` tool is developed iteratively, adhering to SAPPO principles and the Orchestrator-driven workflow. Each feature (like a CLI command or a validation module) is treated as a micro-task.

Each micro-task undergoes an immediate Code->Test->Fix **Boomerang Cycle**. For instance, after `@coder` implements a new command, `@tester-core` immediately applies the **Targeted Testing Strategy**:

*   **Core Logic Testing:** Verifying the internal correctness of the command's implementation. This includes testing base cases, recursive steps (if a `:RecursiveAlgorithm` is involved, though none are currently in the core CLI commands), and edge cases. For example, does `ai-dlc scaffold <team>` create the expected directory structure as per the defined `Directory Skeleton`?
*   **Contextual Integration Testing:** Based on Orchestrator-provided context regarding feature relevance and immediate collaborators, testing key interactions. For example, does `ai-dlc generate --input examples/professional_services.yaml --template research/idea_generation.md.j2` correctly use the specified input and template, and does it integrate correctly with the schema validation logic (`:DataValidation`)?

This approach ensures rapid feedback and high quality for each `:SoftwareComponent` of the tool before integration.

## Getting Started / Next Steps

Detailed instructions on setting up and using the AI-DLC Prompt Template Tool can be found in the main [`README.md`](README.md) file.