# AI-DLC Prompt Template Tool

This document provides an overview and guide for the AI-DLC Prompt Template Tool, a command-line interface (`ai-dlc`) designed to standardize and accelerate `:PromptTemplate` creation within the `:AIDevelopmentLifecycle`.

## Overview

The AI-DLC Prompt Template Tool addresses the `:Problem` of managing and standardizing prompt creation for AI development. It provides a structured `:Solution` by enabling teams to define input data schemas, author Jinja2 templates, generate prompts, validate them against custom rules, and redact sensitive information. This approach promotes consistency, reusability, and maintainability of prompts across different AI projects and teams.

The tool is implemented as a CLI application, making it easy to integrate into development workflows and CI/CD pipelines.

## Features

The AI-DLC Prompt Template Tool offers the following key features:

*   **Scaffolding New Prompt Libraries:** Quickly set up a standardized directory structure for a new team's prompt library.
    *   Command: `ai-dlc scaffold <team_name>`
*   **Generating Prompts:** Generate final prompts by rendering Jinja2 templates with input data validated against a JSON schema.
    *   Command: `ai-dlc generate --template <path> --input <path> --schema <path>`
*   **Validating Input Data:** Ensure input YAML data conforms to a specified JSON schema before generation.
*   **Validating Generated Prompts:** Validate the content of generated prompts against custom rules defined in a `.CHECKS.yaml` file.
    *   Command: `ai-dlc validate --prompt <path> --checks <path>`
*   **Redacting Sensitive Data:** Automatically identify and redact sensitive information (like PII) from generated prompts.
    *   Command: `ai-dlc redact <path> [--output-dir <path>] [--dry-run]`

## Installation/Setup

The tool requires `:Technology:Python 3.12` and `:Technology:uv` for dependency management and environment setup.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-org/ai-dlc-prompts-stage0.git
    cd ai-dlc-prompts-stage0
    ```
2.  **Set up a virtual environment and install dependencies:**
    Using `uv`:
    ```bash
    uv venv
    source .venv/bin/activate # or use uv pip run ... without activation
    uv sync --all-extras
    ```
    Alternatively, using standard `venv` and `pip`:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -e .[dev]
    ```

## Basic Workflow / Getting Started

This section walks through a typical workflow for creating and managing prompts using the AI-DLC Prompt Template Tool.

### Step 1: Scaffold a New Team Library

Start by scaffolding a new directory structure for your team's prompt library. Replace `professional_services` with your team's name.

```bash
ai-dlc scaffold professional_services
```

This command creates the following directory structure:

```
professional_services/
├── templates/  # Jinja2 templates (.md.j2)
├── schemas/    # JSON schemas for input data (.schema.json)
├── examples/   # Example input data (.yaml)
└── checks/     # Custom validation checks (.CHECKS.yaml)
```

### Step 2: Define Input Data Schema

Inside your team's `schemas/` directory, create a JSON schema file (e.g., `professional_services/schemas/team_input.schema.json`) to define the expected structure and types of your input data. This schema is used to validate your YAML input files.

Example `professional_services/schemas/team_input.schema.json`:

```json
{
  "type": "object",
  "properties": {
    "project_name": {
      "type": "string",
      "description": "The name of the project."
    },
    "client_name": {
      "type": "string",
      "description": "The name of the client."
    }
  },
  "required": ["project_name", "client_name"],
  "additionalProperties": false
}
```

### Step 3: Create Input YAML Data

In your team's `examples/` directory, create a YAML file (e.g., `professional_services/examples/project_alpha_data.yaml`) containing the data you want to use to populate your templates. This data must conform to the schema defined in Step 2.

Example `professional_services/examples/project_alpha_data.yaml`:

```yaml
project_name: Project Alpha
client_name: Acme Corporation
```

### Step 4: Author Jinja2 Templates

In your team's `templates/` directory, create Jinja2 template files (e.g., `professional_services/templates/idea_gen.md.j2`). These templates use Jinja2 syntax to reference variables from your input YAML data.

Example `professional_services/templates/idea_gen.md.j2`:

```jinja
## Project Idea Generation for {{ project_name }}

Client: {{ client_name }}

Please generate innovative ideas for the "{{ project_name }}" project for our client "{{ client_name }}".
```

### Step 5: Generate Prompts

Use the `generate` command to combine your input data, schema, and template to produce a final prompt. The output is written to standard output, which you can redirect to a file.

```bash
ai-dlc generate \
  --input professional_services/examples/project_alpha_data.yaml \
  --schema professional_services/schemas/team_input.schema.json \
  --template professional_services/templates/idea_gen.md.j2 \
  > generated_prompt.md
```

The generated `generated_prompt.md` file will contain:

```markdown
## Project Idea Generation for Project Alpha

Client: Acme Corporation

Please generate innovative ideas for the "Project Alpha" project for our client "Acme Corporation".
```

### Step 6: Define Custom Validation Checks (Optional)

You can define custom validation rules for your generated prompts in a `.CHECKS.yaml` file (e.g., `professional_services/checks/custom.CHECKS.yaml`). This allows you to enforce specific content requirements or constraints on your prompts. Each check has an `id`, `description`, `type`, and `config`. Supported types include `regex_match` and `keyword_presence`.

Example `professional_services/checks/custom.CHECKS.yaml`:

```yaml
checks:
  - id: require_client_name
    description: Ensures the client name is present in the prompt.
    type: keyword_presence
    config:
      keyword: "Client: "
```

### Step 7: Validate Prompts (Optional)

Use the `validate` command to check a generated prompt against your custom validation rules.

```bash
ai-dlc validate \
  --prompt generated_prompt.md \
  --checks professional_services/checks/custom.CHECKS.yaml
```

The command will report whether the prompt passes or fails the defined checks.

### Step 8: Redact Sensitive Data (Recommended)

Before using generated prompts with AI models, it is highly recommended to redact any sensitive information. Use the `redact` command for this purpose. By default, it redacts in-place. You can use `--output-dir` to save redacted prompts to a different location or `--dry-run` to see what would be redacted without making changes.

```bash
ai-dlc redact generated_prompt.md
# Or to output to a directory:
# ai-dlc redact generated_prompt.md --output-dir redacted_prompts
```

## Command Reference

*   `ai-dlc scaffold <team_name>`: Scaffolds a new team prompt library directory structure.
*   `ai-dlc generate --template <path> --input <path> --schema <path>`: Generates a prompt from a Jinja2 template, input YAML, and JSON schema.
    *   `--template`: Path to the Jinja2 template file (`.md.j2`).
    *   `--input`: Path to the input YAML data file.
    *   `--schema`: Path to the JSON schema file for input data validation.
*   `ai-dlc validate --prompt <path> --checks <path>`: Validates a generated prompt against custom checks.
    *   `--prompt`: Path to the generated prompt file.
    *   `--checks`: Path to the `.CHECKS.yaml` file containing validation rules.
*   `ai-dlc redact <path> [--output-dir <path>] [--dry-run]`: Redacts sensitive data from a prompt.
    *   `<path>`: Path to the prompt file to redact.
    *   `--output-dir`: Optional directory to save the redacted file (preserves original).
    *   `--dry-run`: Optional flag to show redaction without modifying the file.

## Configuration

Custom validation rules are defined in `.CHECKS.yaml` files, as described in the Basic Workflow section.

Currently, the redaction patterns are hardcoded within the [`cli/redact_utils.py`](cli/redact_utils.py) module. Future versions may introduce external configuration options for redaction patterns.

## Targeted Testing Strategy


python -m unittest tests/cli/test_redact_utils.py -v

python -m pytest tests/cli/test_validate.py -v

uv run python -m cli.main validate --prompt prompts_dir --checks test_custom_checks.yaml

During the development of the AI-DLC Prompt Template Tool, a **Targeted Testing Strategy** was employed to ensure the reliability and correctness of each feature. This strategy focused on two key areas:

1.  **CORE LOGIC TESTING:** Rigorous unit tests were written to verify the internal correctness of each function and module, such as schema validation, template rendering, and redaction logic. This ensured that the core functionality performed as expected under various conditions and edge cases.
2.  **CONTEXTUAL INTEGRATION TESTING:** Tests were designed to verify the key interactions between different components of the tool and their expected behavior within the `:ProjectContext`. For example, tests confirmed that the `generate` command correctly integrated schema validation with template rendering, and that the `validate` command correctly applied the rules defined in a `.CHECKS.yaml` file to a generated prompt. This approach provided early feedback on critical integration points without requiring exhaustive end-to-end tests for every possible scenario.

This targeted approach allowed for efficient testing and rapid iteration during development, ensuring a stable foundation for the tool.
