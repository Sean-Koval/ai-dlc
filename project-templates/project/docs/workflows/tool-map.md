# Workflow tool map

AI-DLC defines stable responsibilities and maps them to providers through
`ai-dlc.toml`. Confirm this project's selected roles; omitted capabilities are
not configured provider choices.

[Back to the workflow map](../development-workflow.md)

| Responsibility | Role or service | Default provider | Durable ownership |
| --- | --- | --- | --- |
| Formal behavior | `specs` | OpenSpec | Requirements and scenarios |
| Priority and lifecycle | `tracker` | Linear | Work identity, priority, and status |
| Personal continuity | `knowledge` | Obsidian | Private notes, reflection, and links |
| Review and merge | `scm` | GitHub | Branch, PR, merged SHA, CI runs, and artifacts |
| Deployment evidence | `deploy` | None | Environment evidence when configured |
| Interactive agent | `agent-client` | Claude Code and Codex | Analysis, authoring, and authorized tool use |
| Workflow enforcement | AI-DLC CLI and selected MCP services | Local services | CLI: validation, machine bindings, reconciliation, receipts, and gates; MCP: reviewed work, doctor, and knowledge only |
| Project lifecycle | Copier | Template service | Answers, source revision, preview, and three-way updates |

The complete publish/start/status/finish lifecycle requires configured tracker
and SCM roles. Local OpenSpec and GitHub compatibility fallbacks exist, but do
not select account, repository, or authorization. GitHub uses conventional
`verify.yml` and `main` defaults unless overridden; the tracker has no fallback.
Without tracker or SCM configuration, initialization, adoption, setup, checks,
design, and documentation remain available, but evidence-gated remote
completion does not. A missing specification role may deliberately use the
local OpenSpec fallback when its artifacts exist; otherwise work must be
reviewed with `requires_spec = false`. Knowledge, deployment, and agent clients
are optional.

## Skills by stage

| Stage | Skill |
| --- | --- |
| Reconcile current state | `day-start` |
| Clarify an uncertain problem | `discovery` |
| Preserve product rationale | `prd-draft` |
| Decide on formal behavior | `needs-spec` |
| Translate approved behavior | `spec-from-prd` |
| Triage incoming ideas | `review-inbox` |
| Transfer verified context | `handoff` |
| Close a work period | `day-end` |

Skills provide judgment. Provider instructions define vendor operations.
AI-DLC services own validation and mutation boundaries; no skill bypasses finish
gates or extends user authorization.

## Portable enrollment boundary

A private profile repository owns the portable `ai-dlc-profile.toml` and is
enrolled by pinned revision. A second machine enrolls that same revision but
maintains its own machine binding for paths, account selection, and
environment-variable names. The project repository owns shared policy; an
external password manager, keychain, or secret injector owns credential values
and supplies them transiently through the process environment. Codex and Claude
own their generated client configuration. Never commit `.env` files or
credential values.

`ai-dlc machine status`, `plan`, `apply`, `sync`, and `doctor` own the local
enrollment lifecycle. Local CLI and MCP execution are current; hosted or cloud
execution is a later qualification target. Obsidian create/attach and provider
discovery are next-cycle gaps rather than current provider capabilities.

Machine enrollment mutations are CLI-only in this cycle. MCP exposes exactly
`work_publish`, `work_start`, `work_status`, `work_link`, `work_finish`,
`doctor`, `knowledge_find`, `knowledge_append`, and `knowledge_note`; it does
not expose machine enrollment mutation. These MCP identifiers differ from the
space-separated CLI commands, such as `ai-dlc work publish` and `ai-dlc
knowledge append`.

## Command groups

| Area | Interfaces |
| --- | --- |
| Readiness and context | `ai-dlc doctor`, `ai-dlc context` |
| Project lifecycle | `ai-dlc project init`, `ai-dlc project adopt`, `ai-dlc project sync`, `ai-dlc project setup`, `ai-dlc project check --required`, `ai-dlc project rebind` |
| Agent configuration | `ai-dlc agents render` |
| Work and traceability | `ai-dlc work publish`, `ai-dlc work link`, `ai-dlc work start`, `ai-dlc work status`, `ai-dlc work finish` |
| Provider verification | `ai-dlc provider list`, `ai-dlc provider test` |
| Personal knowledge | `ai-dlc knowledge find`, `ai-dlc knowledge note`, `ai-dlc knowledge append` |
| Profiles and machine setup | `ai-dlc profile show`, `ai-dlc profile migrate`, `ai-dlc profile capture`; `ai-dlc setup plan`, `ai-dlc setup apply` |
| Agent-native access | `ai-dlc mcp serve` — reviewed work, read-only doctor, and selected knowledge services; machine enrollment mutation remains CLI-only |
| Legacy compatibility | `ai-dlc scaffold` |

The local MCP server exposes only the reviewed services listed above; machine
enrollment mutation remains CLI-only. The legacy scaffold command preserves the
retired Rust-era provider interface; it is not the project lifecycle.

When replacing a tool, keep its responsibility stable where possible. Update
configuration, provider contracts, this map, relevant skills, integration
tests, live walkthrough evidence, and project templates together. Rebind
existing work explicitly; do not silently move it between providers. Portable
configuration may name environment variables, but actual secrets, account
choices, and machine-local paths remain outside portable project files.
