## ADDED Requirements

### Requirement: DE-01 Bounded harness review
A shared review preparation service SHALL provide selected documents, relevant local evidence, source revisions and diagnostics to the existing harness with explicit limits and unreviewed material. No model service or external fetching SHALL be implicit.

#### Scenario: Bounded harness review
- **WHEN** only two documents are selected
- **THEN** the review packet includes their bounded evidence and identifies omissions

### Requirement: DE-02 Grounded findings
Review findings SHALL cite actual document passages and supporting evidence, distinguish uncertainty and recommend a disposition for contradictions, unsupported claims, obsolete instructions, unnecessary repetition, missing explanation or vague prose. Evidence SHALL be validated against prepared content.

#### Scenario: Grounded findings
- **WHEN** a finding cites a nonexistent passage or changed source
- **THEN** acceptance rejects the unsupported or stale evidence

### Requirement: DE-03 Reviewed consolidation
Semantic consolidation SHALL remain a reviewed edit preserving unique information, rationale and useful audience-specific summaries. Candidate similarity SHALL not authorize deletion, rewriting formal intent, or project-wide accuracy claims.

#### Scenario: Reviewed consolidation
- **WHEN** two passages paraphrase the same instruction but another summary serves a different audience
- **THEN** review proposes consolidation only for needless overlap and records the useful repetition
