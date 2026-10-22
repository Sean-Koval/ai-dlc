# Workflow tool map

Find the command, MCP tool or skill that each stage of the
[development workflow](../development-workflow.md) uses, and which provider
fills each role by default.

The lifecycle uses stable roles; `ai-dlc.toml` selects their current providers.
Agents can use native tools directly; the configured services provide specific
validation and completion boundaries. The [roadmap](../roadmap.md) distinguishes
planned support from the current interfaces listed here.

## Role to provider mapping

| Stable responsibility | ai-dlc role or service | Current default | Owns |
| --- | --- | --- | --- |
| Formal behavior | `specs` | OpenSpec | Requirements and scenarios |
| Priority and lifecycle | `tracker` | GitHub Issues and Projects | Work identity, priority, and status |
| Personal continuity | `knowledge` | Obsidian | Private notes, reflection, and links |
| Review, merge, and CI identity | `scm` | GitHub | Branches, pull requests, merged SHA, workflow runs, and artifacts |
| Deployment evidence | `deploy` | None by default | Environment-specific release evidence when configured |
| Interactive agent | `agent-client` | Claude Code and Codex | Analysis, judgment, authoring, and tool use under user authorization |
| Deterministic workflow | ai-dlc CLI and selected MCP services | Local Python implementation | Validation, rendering, machine bindings, reconciliation, receipts and gates; MCP exposes reviewed work, doctor, documentation and knowledge |
| Project generation and updates | Template service | Copier | Template answers, source revision, preview, and three-way updates |

Projects may omit roles they do not need. Confirm the actual mapping in the
project's `ai-dlc.toml`; do not infer an account, workspace, repository, or
environment from these defaults.

GitHub Issues and Projects is the default and recommended work tracker with
recorded live evidence. Jira Cloud is kept for the local work lifecycle pending
its live workflow qualification. Plane is unsupported and unqualified: scaffolding
refuses it without `--allow-unsupported`, and doctor reports it as unsupported.
The Linear adapter has been removed.

hangar intake, not ai-dlc, starts agent jobs from tickets; see the
[tracker boundary](../architecture.md#tracker-boundary-with-hangar)
and set `[work] tracker_writes = "finish-only"` where both are used. The
[Jira preparation record](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/verification/jira-cloud-new-work.md)
lists prerequisites and limits; adapter availability alone does not establish
readiness.

The evidence-gated work cycle requires configured tracker and SCM roles. The
runtime keeps compatibility fallbacks for local OpenSpec and GitHub, which choose
no account, repository or authorization. GitHub assumes
`verify.yml` and `main` unless overridden; the tracker has no fallback. Without
those roles, setup, checks, design and documentation still work, but
publish/start/finish does not.

Knowledge, deployment and agent clients remain optional.

## Skill map

| Moment | Skill | Expected judgment output |
| --- | --- | --- |
| Start of work | `day-start` | Reconciled priority, bindings, branch, and evidence |
| Unclear problem | `discovery` | Bounded problem, evidence, assumptions, questions, and next investigation |
| Durable product rationale | `prd-draft` | Reviewed problem, outcomes, scope, constraints, risks, and acceptance |
| Specification decision | `needs-spec` | Explicit decision based on behavior and risk |
| Approved behavior | `spec-from-prd` | Provider-owned requirements and scenarios linked to rationale |
| Incoming idea or note | `review-inbox` | Classification and next action without automatic publication |
| Session or ownership transfer | `handoff` | Verified state, decisions, evidence, risks, and next action |
| End of work period | `day-end` | Concise continuity record and reconciled remote state |

The optional [workflow plugin](workflow-plugin.md) carries
`discovery`, `prd-draft`, `needs-spec`, `spec-from-prd`, `review-inbox`, `handoff`,
`document-review`, `document-organize`, `design-brief` and `design-evaluate`,
namespaced as `ai-dlc-workflow:<skill>`, plus an `ai-dlc-workflow` guide skill.
`day-start` and `day-end` stay with personal profiles.

The plugin's hooks run without the CLI. They deny destructive commands, delegate
to `ai-dlc hook` only in adopted repositories outside hangar, and never apply
the bound-push policy in hangar. Repository-rendered hooks below require the CLI.

Skills provide judgment patterns; provider instructions define vendor
operations; ai-dlc services own validation and mutation boundaries. A skill
cannot bypass completion gates or expand the user's authorization.

## Portable enrollment boundary

A private profile repository owns the portable `ai-dlc-profile.toml` and is
enrolled by pinned revision. A second machine enrolls that same revision but
maintains its own machine binding for paths, account selection, and
environment-variable names.

The project repository owns shared policy. An external password manager,
keychain, or secret injector owns credential values and supplies them
transiently through the process environment. Codex and Claude own their
generated client configuration. Never commit `.env` files or credential values.

`ai-dlc machine status`, `plan`, `apply`, `sync`, and `doctor` own the local
enrollment lifecycle; machine enrollment mutations are CLI-only. Existing
Obsidian vaults support portal linking and explicit local project mounts; vault
creation is not provided. Guided setup exists for GitHub, Jira Cloud and the
unsupported Plane adapter.

MCP includes `work_context`, `work_publish`, `work_start`, `work_status`,
`work_link`, `work_finish`, `doctor`, `knowledge_find`, `knowledge_append` and
`knowledge_note`, alongside project-document and workspace tools. These
identifiers differ from the space-separated CLI commands, such as
`ai-dlc work publish`.

## Command and service map

| Area | Interfaces | Effect |
| --- | --- | --- |
| Readiness and context | `ai-dlc doctor`, `ai-dlc next`, `ai-dlc context` | Checks the selected environment; `next` and `context --brief` show local next actions without consulting the tracker |
| Consumer onboarding | `ai-dlc project onboard --root PATH` | Returns a read-only plan; exit 0 means actions are available, not completed |
| Environment comparison | `ai-dlc machine status --root PATH --export FILE`, `ai-dlc machine status --compare LEFT RIGHT` | Exports permitted local facts and compares two reports; see [report modes and exit codes](../runbooks/machine-enrollment.md#compare-selected-environments) |
| Project creation | `ai-dlc project init`, `ai-dlc project adopt` | Initializes a project or previews/applies conflict-safe adoption |
| Project maintenance | `ai-dlc project sync`, `ai-dlc project rebind` | Staged Copier updates; previews/applies reviewed provider rebinding |
| Project execution | `ai-dlc project setup`, `ai-dlc project check --check ID`, `ai-dlc project check --required` | Runs selected checks or the full required set and emits receipts that list every required ID; `--target` is `local` or `github-actions` |
| Agent configuration | `ai-dlc agents render` | Previews, applies, or verifies owned project/personal client configuration |
| Local work drafting | `ai-dlc work new WORK_ID [--from-issue REF]` | Creates an unreviewed record from explicit fields or a configured tracker read; does not publish or initialize mutation state |
| Work lifecycle | `ai-dlc work publish`, `ai-dlc work start`, `ai-dlc work pr`, `ai-dlc work finish` | Reconciles tracker state, binds work to a branch and enforces completion gates; `work finish <id> --at-merge` finishes from the exact merge commit |
| Local work inspection | `ai-dlc work status`, MCP `work_status` | Reads the local record, bindings and active/archived specification state without querying tracker status |
| Specification finalization | `ai-dlc work archive` | Archives this work's OpenSpec change, promotes specifications, repoints the record and commits only affected files before merge |
| Traceability | `ai-dlc work link` | Links PR, specification, branch, deployment, or tracker evidence and commits only the work record by default |
| Provider inspection and connection | `ai-dlc provider list`, `ai-dlc provider test`, `ai-dlc provider connect` | Discovers adapters, runs isolated contract or authorized live checks, and previews/applies an explicitly reviewed provider connection |
| Tracker migration | `ai-dlc project tracker-migrate` | Reviews a default-only switch or selected existing-ticket mappings with local recovery evidence |
| Personal knowledge | `ai-dlc knowledge find`, `ai-dlc knowledge note`, `ai-dlc knowledge append`, `ai-dlc knowledge check` | Reads or writes explicitly selected vault material; `check` validates learning frontmatter read-only |
| Configuration profiles | `ai-dlc profile show`, `ai-dlc profile migrate`, `ai-dlc profile capture` | Resolves provenance, previews schema migration, or captures supported preferences |
| Machine provisioning | `ai-dlc setup plan`, `ai-dlc setup apply` | Previews or applies selected workstation modules and personal agent configuration |
| Agent-native access | `ai-dlc mcp serve` | Exposes reviewed work, read-only doctor, documentation, workspace and knowledge services through local MCP |

### Optional publication hook

`bound-push` is selected separately through a supported client's `required_hooks`.
Its project-only `agents.bound_push_policy` defaults to `all-branches`, requiring
reviewed tracker-bound work for covered push and PR-create commands. Explicit
`tracked-branches` also allows a known branch with no associated record after a
complete readable inventory. Every associated record must still pass local
validation; malformed or unreadable inventory cannot grant an exemption.

Selecting a policy alone does not enable a hook or expand supported client
coverage. Hook coverage is a minimum client version per client (`claude-code`
2.1.0, `codex` 0.151.0 in `agents/capabilities.toml`). A configured version
below it refuses, a newer one is accepted and an unset version is accepted with
a warning. The floor is not a qualification record. See
[the workflow decision](../development-workflow.md#when-a-work-record-is-needed)
for the configuration example.

This offline check does not query the remote tracker or enforce arbitrary shell
commands. Destructive denials, native approval, review, required checks and
exact-merge completion evidence retain their existing boundaries.

## Artifact ownership

The reviewed work record binds the repository, the specification provider and
the tracker. The branch, PR, merge and CI evidence it produces are what the
finish gates check before the tracker item closes.

- Repository: architecture, PRDs, design context, ADRs, runbooks, code, tests.
- Specification provider: formal behavior and scenarios.
- Tracker: priority, work identity, lifecycle state.
- SCM/CI: review, merge identity, test artifacts, and receipts.
- Knowledge provider: private continuity and links to durable artifacts.
- Portable project configuration: provider roles and the names of required
  environment variables; the machine binding holds account choices and paths;
  a password manager, keychain or secret injector holds the values.

## CI and release evidence

The generated GitHub workflow runs reviewed bootstrap artifacts and required
checks, then uploads a receipt. Single-job projects use `ai-dlc-receipt`.
Matrix repositories list every exact expected artifact in
`scm.receipt_artifacts`; finish reads this declaration from the authenticated
merged revision and validates every receipt.

Projects supply the published `bootstrap/release.sh` and its artifact manifest
rather than an unpinned download URL. Packaging a skill is not evidence that it
changes agent behavior; behavioral evaluation moved to
[flightdeck](https://github.com/Sean-Koval/flightdeck) (see the
[migration note](../migration.md#ai-dlc-eval-removed)).

## Evolving the toolset

When replacing or adding a tool:

1. Keep the lifecycle stage and responsibility stable where possible.
2. Update `ai-dlc.toml`, provider contracts, and machine credential references.
3. Describe the new provider here and remove claims that no longer apply.
4. Update relevant skills only when the judgment pattern changes.
5. Rebind existing work through reviewed mappings; provider changes apply to
   new work by default.
6. Add contract and integration tests plus a live walkthrough for externally
   mutating providers, and update diagrams and templates in the same change.

Never place secret values, account identifiers, or machine-local paths in this
map; name a required environment variable, never its value.

## Optional Design PM route

For interface work, `design-brief` links the shaped outcome and RQ IDs to a
draft brief, reviewed task rubric and explicit budget. The user's existing
visual tool performs generation. `design-evaluate` records candidate-specific
observations, required failures, ratings and unverified checks. No extra
service, fixed model or paid tool is required. Follow
[design to implementation](design-to-implementation.md#optional-interface-evaluation)
for the four portable templates; the tracker and finish gates stay authoritative.

## Documentation and private workspace tools

??? note "MCP documentation and workspace tools"

    | MCP tool | CLI counterpart | Purpose |
    |---|---|---|
    | `project_docs_impact` | `docs review` | Find mapped documents and unmapped changes for an explicit Git comparison |
    | `project_docs_disposition` | `docs review --disposition` | Emit content-bound reviewed decisions without writing evidence |
    | `project_docs_record` | `docs review --disposition --evidence-id` | Merge reviewed decisions into one work item's evidence file, keeping decisions whose bound content is unchanged |
    | `project_docs_gate` | `docs gate` | Check current dispositions and new objective debt |
    | `project_docs_inventory` | `docs check --inventory` | Discover repository Markdown paths, exclusions and unavailable paths without reading bodies |
    | `project_docs_search` | `docs search` | Search `docs/`, `openspec/` and per-call declared Markdown under one body budget; returns canonical paths, digests and explicit omissions |
    | `project_docs_read` | `docs read` | Read one complete eligible project document within a byte budget; undeclared root or legacy files are refused |
    | `project_docs_review` | `docs review --report` | Prepare bounded selected-document context; explicit `source=inventory` permits uncatalogued documents |
    | `project_docs_review_check` | `docs review --check` | Check citations, scope and source bytes; does not certify semantic truth |
    | `project_workspace_preview` | `project workspace-init` | Preview additive private project navigation; CLI apply explicitly creates files |
    | CLI only | `project workspace-init --shell` | Preview the owned bash, zsh or fish PATH section; `--apply` writes after ownership checks |
    | `project_workspace_check` | `project workspace-check` | Report installation, shell activation, each mount binding and link navigation separately; read-only, native client not assessed |

Project-document search and read cover repository files, never private notes;
the `knowledge_*` tools remain for those. Declare additional Markdown per call
with repeated `--source` (MCP `sources`); nothing is persisted. The
[documentation guide](https://github.com/Sean-Koval/ai-dlc/blob/main/project-templates/project/docs/documentation-guide.md#search-and-read-project-documents)
explains ownership, packet review, baselines and workspace use.

### Native project mounts

`ai-dlc project link-vault --mode mount --preview` previews canonical `docs/` and
existing `openspec/` directory mounts; omit `--preview` to apply. The MCP
`project_vault_mount_preview` tool uses the same read-only plan. Portal mode
remains the default, and mounting does not expand private knowledge access.
`ai-dlc project workspace-check` (MCP `project_workspace_check`) diagnoses the
executable, shell activation, bindings and navigation without changing them.

### Session continuity

`ai-dlc work finish <id> --learning FILE` optionally stores an authored learning
through the knowledge provider after completion gates pass. It adds provenance
frontmatter (merged PR, merge commit, author) that
`ai-dlc knowledge check --vault PATH` validates. MCP `work_finish` accepts
`learning` text alongside its existing `handoff`. Missing knowledge leaves the
note pending and preserves completion.

`work start` returns up to five matching learning paths and first lines; read
relevant notes before implementing. The session-start hook recalls notes for the
branch's bound work record. Stop reminders use only ignored local friction
counts and never transmit them.

### Local frontend evidence

The optional node `frontend` capability supplies a Playwright smoke check.
`ai-dlc design capture` writes viewport screenshots and a manifest for
`design-evaluate`; browser installation belongs to explicit setup. A named state
waits for its visible selector and does not certify untested interactions.
See [frontend smoke and capture](design-to-implementation.md#frontend-smoke-and-capture-evidence).

## Local FDE engagement documents

`ai-dlc fde scaffold SLUG --title TITLE` creates an engagement charter, seven
stage landing pages and portable guidance beneath repository docs; `--dry-run`
returns the proposed content without writing. `ai-dlc fde check SLUG` validates
structure, lifecycle states and preceding exit evidence. See the
[FDE runbook](../runbooks/fde-documents.md); Confluence publication is not
implemented.
