# backend-capability-pack Specification

## Purpose
TBD - created by archiving change backend-capability-pack. Update Purpose after archive.
## Requirements
### Requirement: BE-01 Pinned API contract validation
The optional backend capability SHALL render docs/api/openapi.yaml as a valid OpenAPI 3.1 document with one health endpoint and register it in the documentation catalog. It SHALL add a required api-contract check using an exact pinned validator version for every supported preset. Setup SHALL prepare the validator; checks SHALL run offline after setup and SHALL report malformed contract failures. Capability omission SHALL preserve existing scaffolds. HTTP interface guidance SHALL require updating the contract in the same PR and referencing it as artifacts.contract.

#### Scenario: Python backend is initialized
- **WHEN** a Python project is initialized with the backend capability and setup completes
- **THEN** required checks validate its health contract offline, and corrupting the YAML fails api-contract with validator diagnostics

#### Scenario: Node backend is initialized
- **WHEN** a Node project is initialized with the backend capability
- **THEN** setup prepares an exact pinned Redocly validator and its required contract check refuses package installation and uses offline execution

#### Scenario: Other presets request backend
- **WHEN** generic or Rust requests backend
- **THEN** a pinned Python validator and runtime support are selected without creating a backend provider role

### Requirement: BE-02 Optional FastAPI contract drift
Python backend projects SHALL include api-contract-drift. It SHALL skip cleanly when no src/<pkg>/app.py exposes a FastAPI app, and compare the exposed OpenAPI object with the committed contract when exactly one exists. Differences SHALL fail with a readable diff without rewriting the contract. Broken imports and ambiguous candidates SHALL fail visibly. Other presets SHALL NOT run framework drift checks.

#### Scenario: No FastAPI application exists
- **WHEN** a Python backend project has no FastAPI app in the supported location
- **THEN** drift validation reports a skipped check and exits successfully

#### Scenario: Application schema changed
- **WHEN** the FastAPI application's OpenAPI object differs from the committed contract
- **THEN** drift validation fails and prints the changed contract without modifying files

#### Scenario: Application is re-exported or created by a factory
- **WHEN** the supported app.py exposes a FastAPI app imported or constructed through another module
- **THEN** drift validation compares that exported instance regardless of where FastAPI was imported

