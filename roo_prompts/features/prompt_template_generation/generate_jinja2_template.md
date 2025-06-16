# Plan for Jinja2 Template Generation Feature

## 1. Feature Overview (:SystemFunctionality)

This feature implements a 'meta Jinja creation prompt' :ArchitecturalPattern, specifically a :GeneratorPattern.
*   **Input (:UserInput):** The system accepts a simple, high-level user string describing the desired Jinja2 template structure and content. This string acts as a directive for the meta-prompt.
*   **Process (:Logic):** A core processing logic, driven by the user input string, interprets the user's intent and orchestrates the generation of the Jinja2 template. This involves selecting appropriate Jinja2 constructs (loops, conditionals, variables) based on the input and integrating data from a specified schema.
*   **Output (:GeneratedArtifact):** The output is a complete, syntactically correct, and functionally relevant Jinja2 template file.

## 2. Schema Integration (:DataContract)

The generation process MUST incorporate variables defined in a file named `schemas/example_schema.json` (:DataSource).
*   **Schema Location and Structure:** The `schemas/example_schema.json` file is expected to reside in the `schemas/` directory relative to the project root. It should be a valid JSON file defining the structure and types of data that will be available to the Jinja2 template during rendering. A typical structure might involve nested objects and arrays.
*   **Variable Identification (:DataFlow):** The generation logic will parse `schemas/example_schema.json` to identify available variable names and potentially their data types or structure.
*   **Template Variable Injection (:TemplateVariableInjection):** Based on the user's input string and the identified schema variables, the generation logic will intelligently place Jinja2 variable expressions (e.g., `{{ variable_name }}`) within the generated template. The placement logic will attempt to infer the user's intent regarding where specific data points should appear in the final rendered output.

## 3. User Guidance & Evaluation (:UserExperience, :QualityAssurance)

*   **User Input Guidance (:UserExperience):** The user's input string will directly influence the structure and content of the generated template. The system will interpret keywords, phrases, and potentially simple structural indicators within the input string to guide the meta-prompt. Clear documentation and examples will be provided to help users craft effective input strings, mitigating potential :Ambiguity. Error handling will be implemented for inputs that are too vague or contradictory.
*   **Template Evaluation (:QualityAssurance):** The generated template's :Correctness (syntactical validity, proper variable injection) and :FitnessForPurpose (alignment with user intent and schema) will be evaluated. This could involve:
    *   Syntactic validation of the Jinja2 output.
    *   Rendering the template with sample data conforming to `schemas/example_schema.json` and comparing the output against expected results for key scenarios.
    *   Providing feedback to the user on potential issues or areas for refinement.

## 4. Purpose & Stakeholders (:SystemGoal)

The overarching goal of this feature is to create prompts/tools (:ReusableAsset) that expedite and combine human and AI development efforts for various teams. By automating the initial creation of Jinja2 templates based on high-level directives and schema information, developers can save time and reduce manual errors, focusing instead on refinement and complex logic.

## 5. SAPPO Considerations

*   **Potential :Problems:**
    *   **:Complexity:** Designing a robust meta-prompt capable of interpreting diverse user inputs and generating varied templates is complex.
    *   **:Usability:** Ensuring the user input string is intuitive and powerful without becoming overly complicated is a challenge.
    *   **:Maintainability:** As the system evolves, maintaining the mapping between user input patterns, schema interpretation, and Jinja2 generation logic could become difficult.
    *   **:Scalability:** Generating highly complex or very large templates efficiently might pose performance challenges. Handling a wide variety of schema structures could also impact scalability.
    *   **:Ambiguity:** User input strings can be inherently ambiguous, leading to unexpected or incorrect template generation.
    *   **:Reliability:** Ensuring the generated templates are consistently correct and functional is critical.
*   **Suggested :Solution Approaches:**
    *   Employ a structured approach to meta-prompt design, potentially using a layered architecture where different parts handle input parsing, schema mapping, and template assembly.
    *   Start with a limited scope of supported user input patterns and gradually expand based on user feedback.
    *   Implement clear internal representations of the desired template structure derived from user input and schema data.
    *   Utilize robust testing, including unit tests for parsing/mapping logic and integration tests for end-to-end generation and rendering.
    *   Provide clear error messages and debugging information when generation fails or results in unexpected output.
*   **SAPPO :Technology:** Jinja2 is the core templating technology used. The implementation will likely involve Python libraries for parsing JSON schemas and interacting with the Jinja2 engine.

## TDD Anchors (Core Logic Testability)

To support the Targeted TDD cycle, the following core logic aspects should have specific tests:

1.  **Input Parsing:** Tests should verify that the system correctly parses various user input strings and extracts the intended structural and content directives.
    *   *Expected Behavior:* Given input "Create a list of users with their emails", the parser identifies "list", "users", and "emails" as key elements.
    *   *Expected Behavior:* Given input "Generate a table for products showing name and price", the parser identifies "table", "products", "name", and "price".
2.  **Schema Variable Identification:** Tests should confirm that the system accurately reads `schemas/example_schema.json` and identifies all available variable paths.
    *   *Expected Behavior:* Given a schema `{"user": {"name": "string", "email": "string"}}`, the system identifies `user.name` and `user.email`.
    *   *Expected Behavior:* Given a schema `{"products": [{"name": "string", "price": "number"}]}`, the system identifies `products` (as a list), `products.name`, and `products.price`.
3.  **Variable Injection Logic:** Tests should verify that the system correctly maps identified schema variables to appropriate Jinja2 syntax and places them logically within the generated template structure based on user input.
    *   *Expected Behavior:* Given user input "list of users with emails" and schema `{"user": {"name": "string", "email": "string"}}`, the generated template includes `{{ user.name }}` and `{{ user.email }}` within a list structure (e.g., `<ul><li>...</li></ul>`).
    *   *Expected Behavior:* Given user input "table for products showing name and price" and schema `{"products": [{"name": "string", "price": "number"}]}`, the generated template includes a Jinja2 loop over `products` and places `{{ item.name }}` and `{{ item.price }}` within table cells (`<td>...</td>`).
4.  **Error Handling:** Tests should ensure the system handles invalid or ambiguous inputs gracefully, providing informative error messages.
    *   *Expected Behavior:* Given contradictory input, the system returns an error indicating the conflict.
    *   *Expected Behavior:* Given input requesting variables not present in the schema, the system returns an error or warning.

These tests will form the basis for `@tester-core` to verify the core logic of the template generation feature.