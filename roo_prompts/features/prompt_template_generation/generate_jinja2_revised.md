# Revised Implementation Plan for Jinja2 Template Generation Feature

This plan consolidates the implementation into two lean, LLM-driven modules—Meta-Prompt Constructor and Template Renderer—each with clear sub-phases, testing anchors, and validation hooks.

---

## Phase 1: Meta-Prompt Constructor

> **Goal:** Build a single Jinja2-powered “skeleton” prompt that, when rendered with user inputs and schema JSON, produces a comprehensive ChatGPT prompt to generate the final template.

### Sub-phase 1.1: Skeleton Prompt Design  
- **Deliverable:** `skeleton.j2` file containing the master meta-prompt structure.  
- **Contents:**  
  1. **System block** describing role, task, directives, and schema.  
  2. **Stepwise instructions**:  
     - Propose high-level structure (sections, lists, tables).  
     - Map each schema entity to loops/placeholders.  
     - Insert `VALIDATION:` comments for user review.  
     - Return only the completed Jinja2 template in Markdown.  
- **TDD Anchors:**  
  - Confirm that `skeleton.j2` renders correctly when given sample inputs.  
  - Validate that all placeholders (`{{ role }}`, `{{ schema }}`, etc.) are present.

### Sub-phase 1.2: Prompt Assembly Logic  
- **Deliverable:** Python function `build_meta_prompt(role, task, directives, schema)`  
- **Steps:**  
  1. Load and render `skeleton.j2` with Jinja2.  
  2. Serialize `schema` to pretty-printed JSON.  
  3. Return the fully assembled string to send to the LLM.  
- **TDD Anchors:**  
  - Given fixed inputs, `build_meta_prompt(...)` includes each section in the correct order.  
  - The rendered prompt includes the word “VALIDATION:” exactly once.

### Sub-phase 1.3: Unit Tests for Meta-Prompt  
- **Tests:**  
  - **Placeholder test:** All expected placeholders are filled.  
  - **Structure test:** Sections appear in the intended sequence.  
  - **Edge cases:** Empty directives list still produces a coherent prompt.

---

## Phase 2: Template Renderer

> **Goal:** Send the assembled meta-prompt to the LLM, parse its response, enforce validation hooks, and output the final `.jinja2.md` file.

### Sub-phase 2.1: LLM Invocation & Response Handling  
- **Deliverable:** Function `render_template_via_llm(prompt_text)`  
- **Steps:**  
  1. Send `prompt_text` to the ChatGPT API (with appropriate role separation).  
  2. Receive and store the raw text response.  
- **TDD Anchors:**  
  - Mock LLM responses to verify correct capture of content.  
  - Ensure API errors surface as exceptions.

### Sub-phase 2.2: Validation Hooks & Re-ask Logic  
- **Deliverable:** Post-processing routine `ensure_validation_section(response_text)`  
- **Steps:**  
  1. Check for the `VALIDATION:` marker.  
  2. If missing or incomplete, re-send a brief follow-up prompt:  
     > “Your template is missing the validation step—please add a ‘VALIDATION:’ section listing fields to confirm.”  
  3. Repeat up to N retries before surfacing an error.  
- **TDD Anchors:**  
  - Simulate missing marker and confirm re-ask behavior.  
  - Simulate incomplete validation and confirm single retry.

### Sub-phase 2.3: File Generation & CLI Integration  
- **Deliverable:** CLI command `generate-template`  
- **Steps:**  
  1. Accept flags: `--role`, `--task`, `--directives`, `--schema-path`, `--output`.  
  2. Invoke Meta-Prompt Constructor and Template Renderer.  
  3. Write final text to `output` (default: `template.jinja2.md`).  
- **TDD Anchors:**  
  - End-to-end CLI test using a dummy schema yields a valid `.md` file.  
  - File contains Jinja2 loops and `VALIDATION:` section.

---

## Quality Evaluation Checklist

| Criterion                          | Recommendation                              |
| ---------------------------------- | ------------------------------------------- |
| **Simplicity**                     | 2 modules, minimal parsing logic            |
| **LLM-Centric Design**             | Meta-prompt does structural heavy lifting   |
| **Prompt-Engineering Best Practices** | Explicit system/user blocks, stepwise tasks |
| **Validation Hooks**               | In-prompt `VALIDATION:` + re-ask loop       |
| **Role/Task Adaptivity**           | Fully data-driven via the skeleton template |

---

*With this plan, implementation stays focused on minimal glue code, leverages LLM strengths, and guarantees high-quality, role-aware Jinja2 templates with built-in user validation.*
