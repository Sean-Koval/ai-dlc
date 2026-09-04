# Architecture

AI-DLC v4 runs as a local Python CLI and library. The CLI owns machine
enrollment mutation; the MCP facade exposes only reviewed work, doctor, and
knowledge services. Project adoption uses Copier; provider adapters isolate
vendor-specific operations; agent skills provide judgment. There is no hosted
orchestration service.

## Boundaries

Configuration resolves five ownership layers with provenance:

1. A private Git profile owns portable modules, MCP preferences, workflow
   choices, and logical credential requirements. Pin an exact revision before
   enrolling it on every machine.
2. The project repository owns shared project configuration, policy, durable
   architecture, decisions, and runbooks.
3. Each machine binding owns local paths, account selections, and mappings from
   logical credentials to environment-variable names.
4. A password manager, keychain, or process environment owns credential values.
   AI-DLC never records, prints, or synchronizes those values.
5. Codex and Claude user/project configuration owns generated client files;
   AI-DLC re-renders only entries it owns.

Enrollment locks, profile caches, and operation journals are local control
state, not portable authority. The profile is synchronized by its private Git
repository; the project is synchronized by its repository; machine bindings,
credential stores, and local journals stay on their respective machines.

Portable project data selects role providers and checks and may name required
credential environment variables; it never contains their values. Machine data
supplies account choices and local paths, while the process environment or
native sign-in supplies secrets. Workflow services manage reviewed work,
immutable provider bindings, operation reconciliation and evidence-gated
completion. Check services produce receipts. Provider adapters implement
versioned contracts. Renderers generate deterministic client configuration.
Copier owns template answers, original revisions and three-way updates.

## Persistence

The repository stores architecture, design rationale, decisions, runbooks and reviewed work. Formal specifications belong exclusively to the specification provider. Tracker priority/status is authoritative. The personal knowledge provider is not a repository mirror. Local operation journals aid retries; remote reconciliation and fresh evidence remain necessary across machines.

## Deployment and interfaces

Prefer one application with explicit module responsibilities over speculative service decomposition. CLI, MCP, and agent clients share validation where an MCP service is exposed; the CLI alone owns machine enrollment mutation. The local CLI and local MCP are today's primary control plane; hosted or cloud execution is a later qualification target. External provider failures and uncertain mutations remain visible. Credentials are environment references, never template values.

Knowledge ownership stays provider-neutral: private knowledge links durable
repository material but does not mirror it. Obsidian create/attach and provider
discovery are next-cycle capabilities, not implemented behavior.
