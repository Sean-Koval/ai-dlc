## ADDED Requirements

### Requirement: DQ-01 Portable authoring practices
Supported harness guidance and OpenSpec artifact rules SHALL require audience, purpose, canonical placement and evidence appropriate to document type, with concrete examples where useful, without replacing OpenSpec artifact ownership.

#### Scenario: Portable authoring practices
- **WHEN** a harness receives a document task
- **THEN** it finds existing authority before proposing a new file

### Requirement: DQ-02 Separated objective and editorial checks
Optional existing Markdown and Vale integrations SHALL expose objective and stylistic checks separately from factual judgments without implicit tool installation or certification.

#### Scenario: Separated objective and editorial checks
- **WHEN** Vale is not configured or installed
- **THEN** the optional capability is reported honestly without blocking unrelated baseline checks

### Requirement: DQ-03 Honest qualification
The delivery SHALL demonstrate a repository and disposable brownfield workflow using original semantic cases and reviewed judgments. Actual Claude, Antigravity and Obsidian walkthroughs SHALL be recorded separately from fixtures; unavailable company inputs SHALL remain explicitly pending.

#### Scenario: Honest qualification
- **WHEN** generated-file tests pass without a live work-machine walkthrough
- **THEN** evidence records local success and pending live qualification separately
