## Why

Prepare and validate evidence-backed semantic document reviews. Implements the maintainer-approved dependable documentation and knowledge plan of September 10, 2026.

## What Changes

- A shared review preparation service SHALL provide selected documents, relevant local evidence, source revisions and diagnostics to the existing harness with explicit limits and unreviewed material. No model service or external fetching SHALL be implicit.
- Review findings SHALL cite actual document passages and supporting evidence, distinguish uncertainty and recommend a disposition for contradictions, unsupported claims, obsolete instructions, unnecessary repetition, missing explanation or vague prose. Evidence SHALL be validated against prepared content.
- Semantic consolidation SHALL remain a reviewed edit preserving unique information, rationale and useful audience-specific summaries. Candidate similarity SHALL not authorize deletion, rewriting formal intent, or project-wide accuracy claims.

## Capabilities

### New Capabilities
- `document-evidence-review`: Prepare and validate evidence-backed semantic document reviews.

### Modified Capabilities
None. Existing behavior remains compatible except the explicit opt-in extensions described here.

## Impact

Python shared services, CLI/MCP, reusable guidance, behavior tests and verification evidence. Dependencies: documentation-impact-workflow. No publication, vault mirroring, or new model service.
