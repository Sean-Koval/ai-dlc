# Implementation Plan for Jinja2 Template Generation Feature

Based on the feature overview and requirements outlined in the [generate_jinja2_template.md](roo_prompts/features/prompt_template_generation/generate_jinja2_template.md) document, this plan details the development phases and core logic testability for the Jinja2 Template Generation feature, which implements a :GeneratorPattern.

## 1. Development Phases

This feature development can be broken down into the following phases:

### Phase 1: Core Logic Implementation

Focus on building the fundamental components responsible for interpreting user input, processing schema information, and generating the initial template structure.

#### Sub-phase 1.1: Input Parsing (:Logic)

*   **Objective:** Implement the logic to parse the high-level user input (:UserInput) and extract key structural and content directives, as well as the user's **role** and the intended **task/purpose** of the Jinja2 template.
*   **Details:** This involves identifying keywords, phrases, and potential structural indicators within the input to understand the user's intent. The :UserInput can be a simple string or a structured format like YAML, requiring logic to handle both possibilities. The parsing must specifically identify and extract the user's stated role (e.g., "product manager", "developer") and the specific task the template should facilitate (e.g., "breaking down ideas into user stories", "generating API documentation").
*   **SAPPO :Problem Mitigation:** Directly addresses aspects of :Complexity and :Ambiguity by creating a structured interpretation layer for diverse inputs and extracting crucial :Context.
*   **TDD Anchors (Core Logic Tests):**
    *   Verify correct parsing of various user input formats (string, YAML) and extraction of intended directives, **role**, and **task/purpose**.
        *   *Expected Behavior:* Given input "Create a list of users with their emails", the parser identifies "list", "users", and "emails" as key elements.
        *   *Expected Behavior:* Given input "Generate a table for products showing name and price", the parser identifies "table", "products", "name", and "price".
        *   *Expected Behavior:* Given input "As a **product manager**, I need a template to **break down ideas into user stories**", the parser identifies the role "product manager" and the task "break down ideas into user stories".
        *   *Expected Behavior:* Given YAML input specifying `role: developer` and `task: generate API documentation`, the parser correctly extracts these values.

#### Sub-phase 1.2: Schema Variable Identification (:DataFlow)

*   **Objective:** Implement the logic to read and parse the `schemas/example_schema.json` file (:DataSource) to identify available variable names and their structure.
*   **Details:** The system must be able to handle nested objects and arrays within the JSON schema to build a map of available data paths.
*   **SAPPO :Problem Mitigation:** Addresses aspects of :Scalability related to handling different schema structures.
*   **TDD Anchors (Core Logic Tests):**
    *   Confirm accurate reading and identification of variable paths from `schemas/example_schema.json`.
        *   *Expected Behavior:* Given a schema `{"user": {"name": "string", "email": "string"}}`, the system identifies `user.name` and `user.email`.
        *   *Expected Behavior:* Given a schema `{"products": [{"name": "string", "price": "number"}]}`, the system identifies `products` (as a list), `products.name`, and `products.price`.

#### Sub-phase 1.3: Template Generation Logic (:GeneratorPattern)

*   **Objective:** Implement the core logic to generate the Jinja2 template structure and content. This involves mapping identified schema variables to Jinja2 syntax (`{{ variable_name }}`) and placing them logically. Critically, this phase is where the **"meta-prompt"** functionality resides: the system dynamically determines the overall template structure (e.g., lists, tables, sections, specific Jinja2 constructs like `{% for %}`, `{% if %}`) based on the parsed user input, including the extracted **role** and **task/purpose :Context**. The generated Jinja2 template *is* the complex, high-detailed prompt designed to incorporate best practices of prompt engineering and be carefully tailored for the user's specific task.
*   **Details:** This sub-phase combines the results of input parsing (directives, role, task) and schema identification. The logic must interpret the user's role and task to decide *how* to build the template, influencing the selection and arrangement of Jinja2 constructs, static text, and overall prompt structure. For example, a "product manager" needing to "break down ideas" might result in a template with sections for "Idea", "User Stories", and "Tasks", potentially using lists and markdown formatting, explicitly structured as a prompt for an AI to process. A "developer" needing "API documentation" might result in a template using code blocks and structured key-value pairs, formatted as a prompt for generating documentation. This is the "meta-generation" aspect driven by the user's :Context, resulting in a sophisticated, task-specific prompt template.
*   **SAPPO :Problem Mitigation:** Addresses :Reliability by ensuring correct variable mapping and placement, and mitigates :Complexity and :Ambiguity in template generation by using the user's :Context to guide structural decisions and produce a well-engineered prompt template.
*   **TDD Anchors (Core Logic Tests):**
    *   Verify correct mapping of schema variables to Jinja2 syntax and logical placement based on user input.
    *   Verify that the generated template structure (Jinja2 constructs, layout, static text) is appropriate for the parsed **role** and **task/purpose**, reflecting prompt engineering best practices for the given task.
        *   *Expected Behavior:* Given user input "list of users with emails" and schema `{"user": {"name": "string", "email": "string"}}`, the generated template includes `{{ user.name }}` and `{{ user.email }}` within a list structure (e.g., `<ul><li>...</li></ul>`).
        *   *Expected Behavior:* Given user input "table for products showing name and price" and schema `{"products": [{"name": "string", "price": "number"}]}`, the generated template includes a Jinja2 loop over `products` and places `{{ item.name }}` and `{{ item.price }}` within table cells (`<td>...</td>`).
        *   *Expected Behavior:* Given role "product manager" and task "break down ideas", the generated template includes sections like "Idea", "User Stories", and "Tasks" with appropriate formatting (e.g., markdown lists) and explicit instructions formatted for an AI prompt.
        *   *Expected Behavior:* Given role "developer" and task "generate API documentation", the generated template includes sections for API endpoints, parameters, and responses, potentially using code blocks, structured as a prompt for generating documentation.

### Phase 2: Integration & Refinement

Focus on integrating the core logic components, implementing error handling, and establishing quality assurance mechanisms.

#### Sub-phase 2.1: Schema Integration (:DataContract)

*   **Objective:** Ensure seamless integration with the `schemas/example_schema.json` file as the definitive source for available data variables.
*   **Details:** Refine the schema reading and parsing to be robust against variations in JSON structure and handle potential file system issues.

#### Sub-phase 2.2: User Input Guidance & Error Handling (:UserExperience)

*   **Objective:** Implement mechanisms to handle invalid or ambiguous user inputs gracefully and provide informative feedback.
*   **Details:** Define clear error conditions (e.g., contradictory input, requested variables not in schema) and implement corresponding error messages.
*   **SAPPO :Problem Mitigation:** Directly addresses :Usability and :Ambiguity.
*   **TDD Anchors (Core Logic Tests):**
    *   Ensure the system handles invalid or ambiguous inputs gracefully, providing informative error messages.
        *   *Expected Behavior:* Given contradictory input, the system returns an error indicating the conflict.
        *   *Expected Behavior:* Given input requesting variables not present in the schema, the system returns an error or warning.

#### Sub-phase 2.3: Template Evaluation & Quality Assurance (:QualityAssurance)

*   **Objective:** Implement validation and testing mechanisms for the generated Jinja2 templates.
*   **Details:** Include syntactic validation of the Jinja2 output and potentially rendering the template with sample data to verify correctness and fitness for purpose.
*   **SAPPO :Problem Mitigation:** Addresses :Reliability.

### Phase 3: Documentation & Finalization

Focus on providing necessary documentation and ensuring the feature is ready for use.

*   **Objective:** Create user documentation for crafting effective input strings and finalize the codebase.
*   **Details:** Document the supported input patterns, schema requirements, and error messages. Clean up code and ensure it meets project standards.
*   **SAPPO :Problem Mitigation:** Addresses :Usability and :Maintainability.

## 2. SAPPO Considerations

Throughout the development process, the team must remain mindful of the potential :Problems identified:

*   **:Complexity:** Manage complexity through modular design and clear separation of concerns (parsing, schema handling, generation).
*   **:Usability:** Prioritize intuitive user input patterns and clear documentation.
*   **:Maintainability:** Design for clear internal representations and well-defined interfaces between components.
*   **:Scalability:** Consider potential performance bottlenecks for large schemas or complex templates and design accordingly.
*   **:Ambiguity:** Implement robust parsing and error handling to minimize ambiguity in interpretation.
*   **:Reliability:** Focus on comprehensive testing, particularly the core logic tests defined above, to ensure consistently correct output.

The core :Technology stack involves Python and the Jinja2 library.

## 3. TDD Anchors (Core Logic Testability)

As detailed in the sub-phases above, the following core logic aspects are critical for the Targeted TDD cycle and must have specific tests implemented by `@tester-core`:

1.  **Input Parsing:** Verify correct parsing of various user input strings.
2.  **Schema Variable Identification:** Confirm accurate reading and identification of variable paths from `schemas/example_schema.json`.
3.  **Variable Injection Logic:** Verify correct mapping and logical placement of schema variables in the generated template.
4.  **Error Handling:** Ensure graceful handling of invalid or ambiguous inputs with informative messages.

These anchors provide concrete, testable behaviors for the core logic, enabling immediate verification of the implementation.