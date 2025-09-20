# Jinja2 Template Generation User Guide

This document explains how to use the Jinja2 Template Generation feature, which is implemented following a :ArchitecturalPattern:GeneratorPattern. This feature allows users to generate customized Jinja2 templates based on their specific needs and available data schemas.

## :SystemFunctionality: Template Generation

The core functionality is to take user input and a data schema (:DataSource) and generate a Jinja2 template string. This process is driven by a :GeneratorPattern, where the system interprets the user's intent and the structure of the data to produce a relevant template.

## :UserInput: Providing Context for Generation

The system accepts two main types of user input via the [`parse_user_input()`](cli/template_generation_utils.py:39) function in [`cli/template_generation_utils.py`](cli/template_generation_utils.py). This input provides the necessary :Context for the generator to understand the desired output structure and content.

### Simple String Input

You can provide a natural language string describing the template you need. The system will attempt to parse this string to extract key pieces of :Context:

*   **Role:** Your stated role (e.g., "As a product manager...").
*   **Task:** The specific task the template should help with (e.g., "...I need a template to break down ideas...").
*   **Directives:** Keywords indicating the desired structure or content (e.g., "Create a **list** of **users** with their **emails**").

**Examples:**

*   `"Create a list of users with their emails"` - Directives: `list`, `users`, `emails`
*   `"As a product manager, I need a template to break down ideas into user stories"` - Role: `product manager`, Task: `break down ideas into user stories`, Directives: `[]`
*   `"Generate a table showing product names and prices"` - Directives: `table`, `product names`, `prices`

The system uses simple pattern matching to identify these elements.

### Structured Dictionary/YAML Input

For more explicit control, you can provide input as a dictionary (commonly from a parsed YAML file). This allows you to directly specify the `role`, `task`, and `directives`.

**Example (YAML format):**

```yaml
role: developer
task: generate API documentation
directives:
  structure: table
  main_item: endpoints
  fields: [path, method, description]
```

This structured input is directly consumed by the system, bypassing the string parsing logic.

## :Context: Influencing Template Structure

The :Context provided by your input (role, task, directives) is crucial. The :GeneratorPattern uses this information to make decisions about the overall structure of the generated Jinja2 template.

*   **Directives:** Keywords like "list", "table", "section" strongly influence the top-level HTML or Markdown structure. Directives specifying content (like "users", "emails") guide which variables from the schema should be included.
*   **Role and Task:** Specific combinations of role and task might trigger predefined template structures optimized for those scenarios (e.g., a template format useful for a "product manager" breaking down "user stories").

## Crafting Effective Directives

To get the best results, be clear and specific in your directives, especially when using simple string input.

*   Specify the desired structure (e.g., "list", "table", "sections").
*   Identify the main items or entities you want to list/table/section (e.g., "users", "products", "ideas").
*   List the specific fields or attributes you want included for each item (e.g., "name", "email", "price", "description").

**Examples of effective directives:**

*   `"list of tasks with status and due date"`
*   `"table showing customer name, ID, and last order date"`
*   `"sections for each project, including title and description"`

## Using the :DataSource: Schema Variables

The template generator relies on a provided data schema, such as [`schemas/example_schema.json`](schemas/example_schema.json), which acts as the :DataSource. This schema defines the available variables and their structure.

The generator will attempt to map the entities and fields mentioned in your directives to the variables defined in the schema. For example, if your directives include "users" and "emails", and the schema contains a structure like `{"users": [{"name": "...", "email": "..."}]}`, the generator will understand to create a loop over the `users` array and access the `name` and `email` properties within the loop (e.g., `{{ user.name }}`, `{{ user.email }}`).

## Error Handling

The system includes error handling to provide feedback on problematic input or generation issues, helping to mitigate :Problem:Usability and :Problem:Ambiguity.

*   [`InvalidUserInputError`](cli/template_generation_utils.py:17): Raised when your input contains contradictory directives that make it impossible to determine a clear structure.
    *   **Example Input:** `"Create a list and a table of users"` (Requests two mutually exclusive structures).
*   [`SchemaMismatchError`](cli/template_generation_utils.py:28): Raised if your directives request variables or structures that are not found in the provided schema or are incompatible with the requested structure (e.g., asking for a "table" of a single string variable).
    *   **Example Input:** Directives: `["table", "non_existent_variable"]`, where `non_existent_variable` is not in the schema.
*   `GeneratedTemplateSyntaxError` (wrapped in a `ValueError`): Raised if the internal generation process somehow produces a Jinja2 template string that is syntactically invalid. This indicates an internal issue with the generator itself, not typically user input.

By understanding these input methods, the role of :Context and the schema, and the potential errors, you can effectively use the Jinja2 Template Generation feature.