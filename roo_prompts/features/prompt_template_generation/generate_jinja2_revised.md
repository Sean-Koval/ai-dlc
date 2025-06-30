# Revised Implementation Plan for Jinja2 Template Generation Feature

This plan consolidates the implementation into two lean, LLM-driven modules—Meta-Prompt Constructor and Template Renderer—each with clear sub-phases, testing anchors, validation hooks, and a basic Gemini Gen-AI SDK client for LLM calls.

---

## Phase 1: Meta-Prompt Constructor

**Goal:** Build a single Jinja2-powered “skeleton” prompt that, when rendered with user inputs and schema JSON, produces a comprehensive prompt to feed into Gemini.

### Sub-phase 1.1: Skeleton Prompt Design
- **Deliverable:** `skeleton.j2` file containing the master meta-prompt structure.

**Contents:**
1. **System block** describing role, task, directives, and schema.  
2. **Stepwise instructions:**
   - Propose high-level structure (sections, lists, tables).
   - Map each schema entity to loops/placeholders.
   - Insert `VALIDATION:` comments for user review.
   - Return only the completed Jinja2 template in Markdown.

**TDD Anchors:**
- Confirm that `skeleton.j2` renders correctly when given sample inputs.  
- Validate that all placeholders (`{{ role }}`, `{{ schema }}`, etc.) are present.

### Sub-phase 1.2: Prompt Assembly Logic
- **Deliverable:** Python function `build_meta_prompt(role, task, directives, schema)`

**Steps:**
1. Load and render `skeleton.j2` with Jinja2.  
2. Serialize `schema` to pretty-printed JSON.  
3. Return the fully assembled string to send to the LLM.

**TDD Anchors:**
- Given fixed inputs, `build_meta_prompt(...)` includes each section in the correct order.  
- The rendered prompt includes the word “VALIDATION:” exactly once.

### Sub-phase 1.3: Unit Tests for Meta-Prompt
**Tests:**
- **Placeholder test:** All expected placeholders are filled.  
- **Structure test:** Sections appear in the intended sequence.  
- **Edge cases:** Empty directives list still produces a coherent prompt.

---

## Phase 2: Template Renderer

**Goal:** Send the assembled meta-prompt to Gemini via the Gen-AI SDK, parse its response, enforce validation hooks, and output the final `.jinja2.md` file.

### Sub-phase 2.1: Basic LLM Client & Invocation

#### 2.1.1: Authentication Setup
- **Option A:** Use service-account JSON  
  ```bash
  export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
- **Option B:** Use gcloud auth 
  gcloud auth application-default login

  **Note:** You may need to specify authentication scopes to access the Generative Language API. If you encounter a `403` error, run:
  `gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform`

#### 2.1.2 LLM Client Class
# llm_client.py
import generativeai

class GeminiClient:
    def __init__(self, model_name: str = "models/text-bison-001"):
        # SDK reads GOOGLE_APPLICATION_CREDENTIALS or ADC from gcloud
        self.model = model_name
        generativeai.configure()  # No args if ADC is set

    def generate(self, prompt: str,
                 temperature: float = 0.2,
                 max_tokens: int = 1024) -> str:
        """Send prompt to Gemini and return the generated text."""
        response = generativeai.generate_text(
            model=self.model,
            prompt=prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        return response.text

#### 2.1.3: LLM Invocation Function
Deliverable: Function render_template_via_llm(prompt_text)

Steps:

Instantiate GeminiClient().

Call generate(prompt_text).

Return the raw text response.

TDD Anchors:

Mock GeminiClient.generate to verify correct prompt forwarding and response capture.

Ensure API errors raise clear exceptions.

### Sub-phase 2.2: Validation Hooks & Re-ask Logic
Deliverable: Post-processing routine ensure_validation_section(response_text)

Steps:

Check for the VALIDATION: marker.

If missing/incomplete, call GeminiClient.generate(...) with a brief follow-up:

“Please add a VALIDATION: section listing fields to confirm.”

Retry up to N times before surfacing an error.

TDD Anchors:

Simulate missing marker and confirm re-ask behavior.

Simulate incomplete validation and confirm single retry.

### Sub-phase 2.3: File Generation & CLI Integration
Deliverable: CLI command generate-template

Steps:

Accept flags: --role, --task, --directives, --schema-path, --output.

Invoke Meta-Prompt Constructor and Template Renderer.

Write final text to output (default: template.jinja2.md).

### TDD Anchors:

End-to-end CLI test using dummy schema yields valid .md file.

File contains Jinja2 loops and VALIDATION: section.

#### Quality Evaluation Checklist
Criterion	Recommendation
Simplicity	2 modules, minimal parsing logic
LLM-Centric Design	Meta-prompt does structural heavy lifting
Prompt-Engineering Best Practices	Explicit system/user blocks, stepwise tasks
Validation Hooks	In-prompt VALIDATION: + re-ask loop
Role/Task Adaptivity	Fully data-driven via skeleton template