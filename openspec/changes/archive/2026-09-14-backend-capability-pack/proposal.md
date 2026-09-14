# Backend API contract capability

## Why
API changes need a reviewed contract file and a required validator check, carried with their behavior specification.

## What Changes
Add an opt-in backend capability to existing template selection. Render a minimal OpenAPI 3.1 health endpoint and catalog mapping. Prepare exact validator versions during setup; checks use offline cached tools. Python also gets a bounded optional FastAPI schema drift check which skips absent apps and reports readable diffs.

## Capabilities
### Added Capabilities
- backend-capability-pack: BE-01 pinned contract validation and BE-02 optional FastAPI drift.

## Impact
Existing Copier selection and preset manifests, generated contract/catalog/drift script, spec-from-prd guidance, template documentation and regression fixtures. No code generation, mock server or other framework integration.
