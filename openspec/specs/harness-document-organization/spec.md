# harness-document-organization Specification

## Purpose
Provide repository-wide document discovery and evidence-grounded review so harnesses can organize existing content through reviewed Git edits.

## Requirements
### Requirement: DO-01 Repository inventory
CLI and MCP SHALL share a read-only inventory of tracked and nonignored Markdown across the repository, including root and legacy directories, with explicit exclusion and inaccessible/symlink reporting.

#### Scenario: Scattered documents
- **WHEN** a repository has root, docs and legacy Markdown plus ignored and symlinked paths
- **THEN** inventory identifies eligible files without following symlinks or reading excluded bodies

### Requirement: DO-02 Uncatalogued review
Review preparation SHALL accept explicitly selected inventory documents before catalog enrollment and retain bounded reads, source fingerprints, citation validation and explicit omissions.

#### Scenario: Review before enrollment
- **WHEN** a selected root document is absent from the catalog
- **THEN** a review packet includes it and validation rejects changed source bytes

### Requirement: DO-03 Harness organization
A shipped document-organize skill SHALL guide the harness from discovery through content review, reviewed moves/consolidations/archive decisions, ordinary Git edits, link repair and navigation/catalog maintenance; OpenSpec remains canonical.

#### Scenario: Outcome-level request
- **WHEN** a harness receives only an outcome-level organization request for a messy fixture
- **THEN** it uses supplied skills/tools to propose and execute reviewed organization preserving unique content and useful history and producing an inspectable Git diff; a report or empty structure alone is insufficient

