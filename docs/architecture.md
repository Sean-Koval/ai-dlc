# Architecture

This page describes the current implementation. The [product direction](product-direction.md)
and [planned delivery architecture](design/framework-delivery.md) describe the next
increments. UI/UX is one optional workflow; portable setup, replaceable integrations,
and effective greenfield/brownfield development remain the framework's core.

AI-DLC v4 runs as a local Python CLI and library. The CLI owns machine
enrollment mutation; the MCP facade exposes shared work, doctor, knowledge and documentation services. Project adoption uses Copier; provider adapters isolate
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
repository material but does not mirror it. Linked Obsidian portals, additive personal workspaces and explicit local directory mounts are implemented;
native application qualification remains separately recorded. Guided tracker discovery supports Linear and GitHub Issues with
optional Projects; live qualification is recorded separately.

## Tracker capabilities and connection

Work start consumes declared lifecycle capabilities through the provider registry.
A tracker without an in-progress representation leaves its native ticket unchanged
while local branch/work setup advances. A legacy adapter without a capability
declaration retains its unverified fallback; a declared operation that fails is
a visible error. GitHub Project status and native issue completion are separate
facts. Finish gates remain authoritative.

Connection handlers discover service-specific names and identities behind the
common setup entry point. Saved plans bind effective runtime settings and
authored project/work snapshots, with secrets represented only by local
authentication references. Configuration changes and retained-work migration
are separate actions. Native MCP access supplies broader service context; it
does not substitute for these lifecycle contracts. See the
[provider contract](../contracts/README.md),
[GitHub setup guide](github-ticket-setup.md), and
[later adapter boundaries](archive/planning/tracker-adapter-follow-through.md).

## Source layout

| Location under `src/ai_dlc/` | Responsibility |
| --- | --- |
| `cli.py`, `mcp_server.py`, `__main__.py` | Public command and MCP entry points |
| `conformance.py` | Public conformance runner entry point |
| `setup/` | Project adoption, provisioning, readiness and provider connection setup |
| `work/` | Work lifecycle, traceability, journals and explicit tracker migration |
| `environment/` | Machine enrollment, profile sources and credential references |
| `harness/` | Skills, pinned bundles, client rendering, components and hooks |
| `documentation/` | Catalog checks, impact/evidence review, knowledge notes and vault links |
| `providers/` | Contract-backed external service adapters and isolated provider execution |
| `verification/` | Sandbox orchestration and its conformance network proxy |
| `compatibility/` | Supported legacy scaffold behavior |
| `config.py`, `contracts.py`, `provider_definitions.py` | Shared configuration and provider contracts |
| `files.py`, `locking.py` | Shared filesystem boundaries and locking |

These are internal Python packages, not separate deployable services. Public
console entry points remain stable. Internal imports use the responsible package;
there is no duplicate tree of compatibility forwarding modules. Application
services share contracts; provider details stay inside adapters.

`scripts/` holds source bootstrap, repository checks and qualification/release
utility entry points. `scripts/cloud/` holds hosted-harness setup;
`scripts/legacy/sync-cli-templates.sh` refreshes only the historical Rust embedded
snapshot. The obsolete unlocked `check_env.sh` installer has been removed.
`templates/` remains packaged because the legacy scaffold command still uses it.
Do not delete subprocess entry points or assets merely because imports do not
reference them directly.
