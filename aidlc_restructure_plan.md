# AI-DLC Repository Restructure Plan (Expanded)

## 1. Introduction

The goal of this restructure is to organize the `ai-dlc` repository into a scalable and intuitive hub for agentic development resources. This new structure will make it easier for Product Managers, Designers, and Developers to find, use, and contribute to the collection of templates, tools, and documentation. This expanded plan includes specific recommendations for tool-specific configurations like slash commands and rules.

## 2. Critique of Current Structure

The current repository structure is a good starting point but has some limitations:

*   **Lack of Scalability:** The `roo_prompts/` directory is specific to one type of template. As we add templates for Gemini, Claude, and other tools, the root directory will become cluttered.
*   **Unclear Organization:** It's not immediately clear where to find different types of resources (templates vs. documentation vs. tool source code).
*   **Standard Python Project Layout:** The source code for the CLI is in a top-level `cli/` directory, which is not standard for Python projects that are meant to be installable.

## 3. Proposed New Structure

Here is the proposed high-level directory structure, updated to include tool-specific configurations:

```
/
├───docs/
│   ├───index.md
│   ├───getting-started.md
│   ├───contributing.md
│   └───guides/
│       ├───for-developers.md
│       ├───for-pms.md
│       └───for-designers.md
├───src/
│   └───ai_dlc/
│       ├───__init__.py
│       └───cli/
│           └───...
├───templates/
│   ├───claude/
│   │   ├───.claude/
│   │   │   ├───agents/
│   │   │   │   ├───security/
│   │   │   │   │   └───example_security_agent.md
│   │   │   │   ├───infrastructure/
│   │   │   │   │   └───example_infra_agent.md
│   │   │   │   └───product/
│   │   │   │       └───example_product_agent.md
│   │   │   ├───commands/
│   │   │   │   └───example.md
│   │   │   └───settings.json
│   │   ├───.mcp.json
│   │   └───CLAUDE.md
│   ├───cursor/
│   │   ├───.cursor/
│   │   │   ├───commands/
│   │   │   │   └───example.md
│   │   │   ├───rules/
│   │   │   │   └───example.mdc
│   │   │   └───mcp.json
│   │   └───AGENTS.md
│   ├───gemini/
│   │   ├───cli/
│   │   ├───studio/
│   │   └───mcp.json
│   ├───roo/
│   │   ├───slash_commands/
│   │   │   └───example.md
│   │   └───rules/
│   │       └───example.json
│   └───generic/
│       ├───design-specs/
│       └───product-requirements/
├───examples/
│   └───...
├───scripts/
│   └───...
├───tests/
│   └───...
├───.gitignore
├───pyproject.toml
├───README.md
└───uv.lock
```

## 4. Explanation of Key Directories

*   **`docs/`**: Central place for all documentation, including role-specific guides.

*   **`src/`**: Source code for the project's own tooling (like the CLI), following a standard Python `src` layout.

*   **`templates/`**: This is the core of the repository. It holds template files that users can copy into their own projects.
    *   **`templates/claude/`**: Contains templates for configuring the Claude Code tool.
        *   `.claude/agents/`: Holds agent definitions organized by role (e.g., `security`, `product`). The agents themselves are defined as Markdown files with YAML frontmatter.
        *   `.claude/commands/`: Stores slash command templates as Markdown files.
        *   `CLAUDE.md`: A template for the project-wide briefing file.
        *   `.mcp.json`: A template for configuring Model Context Protocol servers.
    *   **`templates/cursor/`**: Contains templates for configuring the Cursor IDE.
        *   `.cursor/commands/`: Stores slash command templates.
        *   `.cursor/rules/`: Stores custom rule templates as `.mdc` files.
        *   `.cursor/mcp.json`: A template for Model Context Protocol integrations.
        *   `AGENTS.md`: A template for simpler, project-wide agent instructions.
    *   **`templates/gemini/`**: For Gemini-specific templates.
         *  `mcp.json`: A template for configuring Model Context Protocol servers.
    *   **`templates/roo/`**: Provides a suggested structure for "Roo Code" templates.
        *   `slash_commands/`: A place to store templates for custom Roo slash commands.
        *   `rules/`: A directory for templates that define specific rules for Roo.
    *   **`templates/generic/`**: For non-agent-specific templates like PRDs or design specs.

*   **`examples/`**: This directory will contain practical examples showing how to use the various templates and tools.

## 5. Migration Plan

1.  **Create the new directories:** `src/`, `src/ai_dlc`, `templates/`, `examples/`, and the new subdirectories within `templates`.
2.  **Move CLI source code:**
    *   Move the contents of `cli/` to `src/ai_dlc/cli/`.
    *   Create `src/ai_dlc/__init__.py`.
    *   Update `pyproject.toml` and `tests/` to reflect the new `src` layout.
3.  **Organize Templates:**
    *   Move the contents of `roo_prompts/` to the new `templates/roo/slash_commands/` directory.
    *   Create the other template directories (`claude`, `cursor`, `gemini`, etc.).
4.  **Structure Documentation:**
    *   Move existing documentation into the new `docs/guides/` structure.
    *   Create initial `index.md`, `getting-started.md`, and `contributing.md`.
5.  **Update `README.md`:** Update the root `README.md` to explain the new, more detailed structure.

This expanded structure provides a robust and conventional foundation for the repository, making it easy for users to find and implement tool-specific configurations.