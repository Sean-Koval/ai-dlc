# Architecture

AI-DLC v4 runs as a local Python CLI and library. The MCP facade calls the same services. Project adoption uses Copier; provider adapters isolate vendor-specific operations; agent skills provide judgment. There is no hosted orchestration service.

## Boundaries

Configuration resolves base, personal, project, and machine scopes with provenance. Portable project data selects role providers and checks and may name required credential environment variables; it never contains their values. Machine data supplies account choices and local paths, while the process environment or native sign-in supplies secrets. Workflow services manage reviewed work, immutable provider bindings, operation reconciliation and evidence-gated completion. Check services produce receipts. Provider adapters implement versioned contracts. Renderers generate deterministic client configuration. Copier owns template answers, original revisions and three-way updates.

## Persistence

The repository stores architecture, design rationale, decisions, runbooks and reviewed work. Formal specifications belong exclusively to the specification provider. Tracker priority/status is authoritative. The personal knowledge provider is not a repository mirror. Local operation journals aid retries; remote reconciliation and fresh evidence remain necessary across machines.

## Deployment and interfaces

Prefer one application with explicit module responsibilities over speculative service decomposition. CLI, MCP and agent clients share the same services and validation rules. External provider failures and uncertain mutations remain visible. Credentials are environment references, never template values.
