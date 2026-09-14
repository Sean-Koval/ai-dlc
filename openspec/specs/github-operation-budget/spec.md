# github-operation-budget Specification

## Purpose
TBD - created by archiving change github-operation-budget. Update Purpose after archive.
## Requirements
### Requirement: GO-01 Bounded compound GitHub operations
The bundled GitHub Issues provider SHALL allow 120 seconds by default for one complete provider operation while retaining the existing 30-second default for each gh request. An explicitly configured timeout SHALL remain authoritative. Other executable provider defaults SHALL remain unchanged. Timeouts SHALL propagate as failures and SHALL NOT authorize completion or fabricate successful journal evidence.

#### Scenario: Healthy compound reconciliation exceeds one request budget
- **WHEN** issue and Project reconciliation completes after 35 seconds with each request within its limit
- **THEN** the default transport permits the complete response and validates it normally

#### Scenario: Explicit limit is exceeded
- **WHEN** the provider explicitly configures 30 seconds and reconciliation exceeds that limit
- **THEN** the operation fails with timeout and normal uncertain-write recovery remains available

#### Scenario: Default operation limit is exhausted
- **WHEN** a bundled GitHub Issues operation exceeds 120 seconds
- **THEN** the operation times out without reporting completion

