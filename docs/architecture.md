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

Prefer one application with explicit module responsibilities over speculative service decomposition. CLI, MCP, and agent clients share validation where an MCP service is exposed; the CLI alone owns machine enrollment mutation. The local CLI and local MCP are the control plane; cloud execution is hangar's. Client rendering is frozen to the existing clients for local repositories and CI (`project setup --target local|github-actions`); hangar renders cloud sandboxes at claim time. Hook support is a per-client minimum version (`agents/capabilities.toml`), not qualification. External provider failures and uncertain mutations remain visible. Credentials are environment references, never template values.

Consumer onboarding is a read-only composition boundary in `setup/onboarding.py`.
It resolves one explicit existing target, target-owned configuration, optional
explicit enrollment identity, host/shell/client support, and existing operation
owners into an ordered schema-1 plan. It does not run previews or apply operations,
open a network connection, launch a subprocess, stage adoption, repair caches, or
persist an orchestration session. The thin `project onboard --root PATH` CLI emits
that plan and maps its state to an exit code; it has no apply mode or MCP endpoint.
For a fresh target, adoption precedes root-scoped machine planning because the
existing machine owner requires the target configuration. Each apply still needs
its separate review. Existing enrollment, machine provisioning, adoption, setup,
rendering, readiness, and target-check services retain their own review, mutation,
recovery, and evidence
boundaries. Project configuration wins over conflicting CLI choices, while omitted
enrollment stays unselected for a self-contained project.

Effective-environment reporting is an opt-in boundary under `environment/`.
The local collector projects selected configuration and observations into a
closed schema before serialization or hashing. Pure schema/identity and comparison
functions do not inspect the host; file access and CLI selection remain separate.
Compound doctor/workspace diagnostics are not collectors because they can execute
health checks or inspect unrelated personal state. Ordinary diagnostics and MCP
doctor retain their existing contracts.

Default reporting executes no commands. Fixed version probes require explicit
permission and have bounded output, time and inherited environment. Unknown
provenance stays unknown; existing raw profile/source/ownership hashes cannot
be exported merely because they passed local integrity checks. The configuration
identity covers only permitted desired fields, and the observation identity adds
known engine/platform/runtime/client/guidance facts. Excluded bytes cannot be
distinguished by covert hashes: incomplete reports remain ineligible for native
evidence reuse even when their digests match. Neither identity authenticates a
machine or substitutes for behavioral checks and native qualification.

Application services signal outcomes in one of two ways. A failure the service detected
raises an exception derived from `ai_dlc.errors.AiDlcError` (`RefusedError` for an
operation refused before any change, `UncertainError` for one whose effect must be
reconciled); the CLI reports every such failure through one handler as `Error: <message>`
on stderr with the exception's exit code, and MCP lets it propagate as a tool error.
A completed service call returns a JSON object that satisfies the
[service result envelope](https://github.com/Sean-Koval/ai-dlc/blob/main/contracts/service-result.schema.json): `status` is the
canonical outcome string, and the values in `ai_dlc.contracts.FAILURE_STATUSES` are the
failures. Results that still carry a boolean verdict key (`valid`, `ready`, `passed`,
`clean`) are authoritative through that key until they migrate to `status`.
`ai_dlc.contracts.succeeded` is the one reader of that envelope; commands that map a
returned result to exit status 1 use it. Bare `ValueError` remains for argument
validation and is caught by the same CLI handler while services move to typed errors.

Knowledge ownership stays provider-neutral: private knowledge links durable
repository material but does not mirror it. Linked Obsidian portals, additive personal workspaces and explicit local directory mounts are implemented;
native application qualification remains separately recorded. Guided tracker discovery supports GitHub Issues with
optional Projects and Jira Cloud; live qualification is recorded separately. Plane is
shipped but unsupported, and the Linear adapter has been removed.

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
[provider contract](https://github.com/Sean-Koval/ai-dlc/blob/main/contracts/README.md),
[GitHub setup guide](github-ticket-setup.md), and
[later adapter boundaries](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/planning/tracker-adapter-follow-through.md).

## Tracker boundary with hangar

Hangar owns tracker intake for agent jobs; AI-DLC keeps its tracker adapters for
the local work lifecycle only. Both may touch the same ticket, so each concern has
one owner:

| Concern | Owner |
| --- | --- |
| Starting agent work from a ticket (Jira status or label, GitHub label or Projects column, Slack, schedules) | hangar intake |
| Ticket write-back during an agent job (queued, started, needs_input, delivered, failed) | hangar |
| Trust and approval of who may start work | hangar, then the governed workspace |
| A developer's local work record, branch binding and specification artifacts | AI-DLC |
| Closing a ticket after merge with CI-receipt evidence (`work finish`) | AI-DLC, run locally by a person |
| Creating tickets from reviewed local work (`work publish`) | AI-DLC |
| Bulk and planning workflows (Projects board setup, tracker migration) | AI-DLC, frozen to bug fixes |

**Collision rule.** While a hangar job works a ticket, AI-DLC must not move that
ticket to in-progress. A repository that also uses hangar intake sets

```toml
[work]
tracker_writes = "finish-only"
```

in `ai-dlc.toml` (project or base layer only). `work start` then binds the branch
and reads, but never writes, the ticket; `work finish` still closes it after the
merged-CI gates. The default, `lifecycle`, keeps the existing start transition.
Both tools may still comment on a ticket. A finish for a ticket that hangar's
delivery already closed reconciles the closed state instead of failing.

Kept adapters: GitHub Issues, GitHub Projects and Jira Cloud. Plane stays shipped
with `supported = false`: scaffolding refuses it without `--allow-unsupported` and
doctor reports it as unsupported and unqualified. The Plane adapter is scheduled
for deletion in the next cleanup unless someone objects by the end of P2. The
Linear adapter has been removed; a configuration that still selects it receives
a typed refusal that names the supported trackers.

## Source layout

| Location under `src/ai_dlc/` | Responsibility |
| --- | --- |
| `cli.py`, `mcp_server.py`, `__main__.py` | Public command and MCP entry points |
| `conformance.py` | Public conformance runner entry point |
| `setup/` | Read-only consumer onboarding plans, project adoption, provisioning, readiness and provider connection setup |
| `work/` | Work lifecycle, traceability, journals and explicit tracker migration |
| `environment/` | Shared bootstrap runtime location and owned shell activation; machine enrollment, pinned profile/team sources, credential references and safe effective-environment reporting/comparison |
| `harness/` | Skills, pinned bundles, client rendering, components, hooks and local design capture |
| `documentation/` | Catalog checks, impact/evidence review, decision-record checks, scoped project-document access, workspace diagnostics, knowledge notes and their shared frontmatter schema (`knowledge_notes.py`), and vault links |
| `providers/` | Contract-backed external service adapters and isolated provider execution |
| `verification/` | Sandbox orchestration and its conformance network proxy; `evaluation/` holds the end-to-end evaluation contracts (generated into `contracts/evaluation/`) the offline planner behind the `eval` CLI group, the isolated Docker attempt lifecycle, the independent evaluator, the suite runner, the driver contract that decides what an attempt runs, the offline report builder and the base and candidate image recipes; its inputs live in top-level `evaluations/`, outside the wheel |
| `config.py`, `contracts.py`, `errors.py`, `provider_definitions.py` | Shared configuration, provider contracts, the result envelope and the exception base |
| `files.py`, `locking.py`, `toml_edit.py` | Shared filesystem boundaries, locking and comment-preserving TOML edits |
| `_windows_storage/` | Private native NTFS handle, identity, account/ACL and publication primitives behind the shared filesystem APIs |

`setup/commands.py` validates the shared POSIX-string, argv and explicit-shell command forms before setup/check execution. Windows core storage uses guarded native handles and per-user locks; Unix paths retain their existing implementation. `harness/windows_render.py` applies owned render snapshots with retained backups and refuses recovery over an intervening edit. Native bootstrap and desktop/client qualification are separate from this core service boundary.

These are internal Python packages, not separate deployable services. Public
console entry points remain stable. Internal imports use the responsible package;
there is no duplicate tree of compatibility forwarding modules. Application
services share contracts; provider details stay inside adapters.

`scripts/` holds source bootstrap, repository checks and qualification/release
utility entry points. `scripts/cloud/` holds hosted-agent setup shims that bootstrap the checkout with the local target; `scripts/check_client_pins.py` compares the module catalog's client pins with hangar's harness lock. The obsolete unlocked `check_env.sh`
installer, the historical Rust crate with its embedded template mirror, and the
script that synchronised them have been removed; the retired Rust plans remain in
git history before tag `docs-prune-2026-10`.
The legacy `templates/` scaffold, its `ai-dlc scaffold` command and the stale root
`copier.yml` were removed; `project init` and `project adopt` copy the packaged
`project-templates/`. Packaged assets must not contain vendored trees or personal
machine paths.
Do not delete subprocess entry points or assets merely because imports do not
reference them directly.

### Workflow plugin

Guidance, hooks and skills reach agents through two paths. `ai-dlc agents render`
writes them into adopted repositories: the AGENTS.md managed section, hooks that
run the hidden CLI-only `ai-dlc hook` command (so they require the CLI) and skill
copies. `scripts/build_workflow_plugin.py` packages the same sources as the
optional Claude Code plugin committed at `plugins/ai-dlc-workflow/`, the
distribution path for team harnesses and sandboxes. It reuses the skill lock and
shared guidance, writes per-component digests to `plugin.lock.json`, and runs as a
drift check inside `scripts/check_generated.py`. The same build writes the Codex
form under `plugins/ai-dlc-workflow/native/codex/` (identical skill bytes, a Codex
`hooks.json`, an AGENTS.md fragment and a `.codex-plugin` manifest) and records
per-file digests, which `scripts/publish_workflow_plugin.py` uses to copy both forms
into a team harness directory without overwriting anything it did not publish. The plugin hooks run
`harness/hook_shim.py`, a standard-library copy that delegates to `ai-dlc hook`
only in adopted repositories with the CLI outside hangar, and otherwise denies
only destructive commands; `harness/hooks.py` imports its classifier. This
repository dogfoods the plugin rather than rendered skill copies (`[agents] skills
= []`); adopted repositories keep rendering both skill trees by default. See the
[plugin README](https://github.com/Sean-Koval/ai-dlc/blob/main/plugins/ai-dlc-workflow/README.md).

### FDE engagement documents

`documentation/fde.py` owns local engagement generation and stage checks behind
the thin `fde` CLI group. It reads only the explicit charter and stage landing
pages, and has no provider or private-knowledge connection. See the
[FDE runbook](runbooks/fde-documents.md) for paths, metadata and publication limits.
