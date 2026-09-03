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
| Workflow enforcement | AI-DLC CLI/MCP | Local services | Validation, bindings, reconciliation, receipts, and gates |
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
| Agent-native access | `ai-dlc mcp serve` |
| Legacy compatibility | `ai-dlc scaffold` |

The local MCP server calls the same services and validation as the CLI. The
legacy scaffold command preserves the retired Rust-era provider interface; it
is not the project lifecycle.

When replacing a tool, keep its responsibility stable where possible. Update
configuration, provider contracts, this map, relevant skills, integration
tests, live walkthrough evidence, and project templates together. Rebind
existing work explicitly; do not silently move it between providers. Portable
configuration may name environment variables, but actual secrets, account
choices, and machine-local paths remain outside portable project files.
