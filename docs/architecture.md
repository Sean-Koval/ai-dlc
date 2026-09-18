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
   choices, logical credential requirements and pinned team-source subscriptions. Pin an exact revision before
   enrolling it on every machine.
2. The project repository owns shared project configuration, policy, durable
   architecture, decisions, and runbooks.
3. Each machine binding owns local paths, account selections, and mappings from
   logical credentials to environment-variable names, plus the person's team roles.
4. A password manager, keychain, or process environment owns credential values.
   AI-DLC never records, prints, or synchronizes those values.
5. Codex and Claude user/project configuration owns generated client files;
   AI-DLC re-renders only entries it owns.

Team-source content is selected from verified local caches and rendered through
project ownership checks. Source commits advance only through explicit machine
sync activation; session-start remote-ref notices never update content. The
teamai adapter reads a supported subset without executing upstream tooling.

Enrollment locks, profile/source caches, and operation journals are local control
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

Application services signal outcomes in one of two ways. A failure the service detected
raises an exception derived from `ai_dlc.errors.AiDlcError` (`RefusedError` for an
operation refused before any change, `UncertainError` for one whose effect must be
reconciled); the CLI reports every such failure through one handler as `Error: <message>`
on stderr with the exception's exit code, and MCP lets it propagate as a tool error.
A completed service call returns a JSON object that satisfies the
[service result envelope](../contracts/service-result.schema.json): `status` is the
canonical outcome string, and the values in `ai_dlc.contracts.FAILURE_STATUSES` are the
failures. Results that still carry a boolean verdict key (`valid`, `ready`, `passed`,
`clean`) are authoritative through that key until they migrate to `status`.
`ai_dlc.contracts.succeeded` is the one reader of that envelope; commands that map a
returned result to exit status 1 use it. Bare `ValueError` remains for argument
validation and is caught by the same CLI handler while services move to typed errors.

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
| `environment/` | Shared bootstrap runtime location and owned shell activation; machine enrollment, pinned profile/team sources and credential references |
| `harness/` | Skills, pinned bundles, client rendering, components, hooks and local design capture |
| `documentation/` | Catalog checks, impact/evidence review, scoped project-document access, workspace diagnostics, knowledge notes and vault links |
| `providers/` | Contract-backed external service adapters and isolated provider execution |
| `verification/` | Sandbox orchestration and its conformance network proxy; `evaluation/` holds the end-to-end evaluation contracts (generated into `contracts/evaluation/`) and the offline planner behind the `eval` CLI group |
| `compatibility/` | Supported legacy scaffold behavior |
| `config.py`, `contracts.py`, `errors.py`, `provider_definitions.py` | Shared configuration, provider contracts, the result envelope and the exception base |
| `files.py`, `locking.py`, `toml_edit.py` | Shared filesystem boundaries, locking and comment-preserving TOML edits |

These are internal Python packages, not separate deployable services. Public
console entry points remain stable. Internal imports use the responsible package;
there is no duplicate tree of compatibility forwarding modules. Application
services share contracts; provider details stay inside adapters.

`scripts/` holds source bootstrap, repository checks and qualification/release
utility entry points. `scripts/cloud/` holds hosted-harness setup. The obsolete unlocked `check_env.sh`
installer, the historical Rust crate with its embedded template mirror, and the
script that synchronised them have been removed; the retired Rust plans remain in
`docs/archive/legacy/`.
`templates/` remains packaged because the legacy scaffold command still uses it.
It carries only this repository's own commands, hooks and workflows: the
third-party agent and command collections once copied into it were removed, and
packaged assets must not contain vendored trees or personal machine paths.
Do not delete subprocess entry points or assets merely because imports do not
reference them directly.

### FDE engagement documents

`documentation/fde.py` owns local engagement generation and stage checks behind
the thin `fde` CLI group. It reads only the explicit charter and stage landing
pages, and has no provider or private-knowledge connection. See the
[FDE runbook](runbooks/fde-documents.md) for paths, metadata and publication limits.
