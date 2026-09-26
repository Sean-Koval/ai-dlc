![AI-DLC — A consistent workflow. Your tools.](docs/assets/ai-dlc-banner.svg)

# AI-DLC

**Portable development setup and workflows for people and coding agents.**

AI-DLC brings project setup, agent guidance, specifications, tickets, documentation,
and verification into one repository-owned workflow. Work in Claude Code or Codex,
keep your preferred tools, and carry the same configuration across machines.
You and your agent do the development; AI-DLC prepares the environment and checks
the evidence needed to finish the work.

## Main features

- **Repeatable setup.** Versioned profiles select runtimes, tools, and personal
  agent settings. Each machine keeps its own paths and account bindings.
- **Project scaffolding and updates.** Start or adopt a generic, Python, Node, or
  Rust project. Copier templates provide shared instructions, documentation,
  setup commands, and checks, with previews for adoption and updates.
- **Shared agent guidance.** Render project instructions, skills, hooks, and MCP
  configuration for supported clients. Subscribe to pinned team repositories,
  filter by role or tag, and import supported Tencent teamai layouts.
- **Tickets connected to delivery.** Bind reviewed scope and specifications to a
  ticket, branch, and PR. Completion verifies the merged revision and its CI
  receipts before closing the ticket.
- **Repository docs and private knowledge.** Search project documents, review
  documentation impact, and check ownership and links. Connect canonical project
  docs to an existing Obsidian vault while keeping personal notes separate.
- **Engagement and design workflows.** Scaffold seven-stage forward-deployed
  engineering (FDE) engagement docs with local stage checks. Optional frontend tooling captures Playwright evidence
  for design review.

## How the tools fit together

```mermaid
flowchart LR
    Scope["Shape<br/>Scope, specs, ticket"] --> Build["Build<br/>Agent, branch, PR"]
    Build --> Verify["Verify<br/>Checks, review, merge"]
    Verify --> Finish["Finish<br/>Merged CI, close ticket"]
```

| Tool | Responsibility |
| --- | --- |
| **AI-DLC CLI + local MCP server** | Setup, configuration rendering, work records, document tools, and completion gates. MCP exposes selected services to agents; machine mutations stay in the CLI. |
| **Claude Code / Codex** | Interactive development using shared instructions and skills for discovery, PRDs, specifications, and handoffs. |
| **uv + mise** | Python environments and dependencies, pinned runtimes, and delegated tool installation. |
| **Copier** | Project templates, recorded template versions, and staged updates. |
| **OpenSpec** | Formal requirements, scenarios, and archived changes when the work needs a specification. |
| **GitHub Issues + Projects / GitHub Actions** | Ticket identity and planning, PR review and merge, and CI evidence. |
| **Obsidian** | Private continuity notes and navigation to canonical repository documents. |

Provider roles are configurable. GitHub Issues + Projects is the recommended
tracker with recorded live evidence; Linear is also supported. Jira Cloud and
Plane adapters are available, with live workflow qualification still pending.
For agent access, register `ai-dlc mcp serve --root /absolute/path/to/project`
as a stdio MCP server in your client. See the [tool map](docs/workflows/tool-map.md)
for available commands, MCP tools, and skills.

## Get started

**Choose an installation:** [v0.4.0](https://github.com/Sean-Koval/ai-dlc/releases/tag/v0.4.0)
is the published release; follow the [release installation steps](docs/runbooks/release-publication.md#install-from-a-release)
for its Unix installers. Its original assets do not support native Windows setup
or structured argv commands. Team-source imports, FDE scaffolding, and native
Windows setup require a source revision containing those changes, even when its
version still reads `0.4.0`.

### Prepare an AI-DLC source checkout

For contributors working on AI-DLC itself, obtain a reviewed source checkout.
On macOS or Linux:

```sh
git clone https://github.com/Sean-Koval/ai-dlc.git
cd ai-dlc
sh scripts/bootstrap.sh --source
```

The Unix bootstrap needs a POSIX shell, curl, CA certificates, tar, and standard
platform utilities. It installs pinned uv, Python, and mise; no preinstalled
Python or Node is needed.

On Windows x64, use 64-bit Windows PowerShell 5.1 in the source checkout on local
NTFS. Preview the native bootstrap, then run it:

```powershell
.\scripts\bootstrap.ps1 -Source -Root $PWD.Path -Plan
.\scripts\bootstrap.ps1 -Source -Root $PWD.Path
```

Native setup does not require WSL, a POSIX shell, or preinstalled Python or Node.
It does require the machine's existing PowerShell policy to permit the reviewed
script. It does not change execution policy, elevate, or edit machine PATH.
Use the printed checkout-specific executable or PATH directories, especially
when another AI-DLC installation exists. For persistent activation, see the
[PowerShell preview and apply procedure](docs/runbooks/machine-enrollment.md#native-windows-setup-and-activation).

After activating this checkout's environment, contributors run
`ai-dlc project check --required`. These are AI-DLC's own engineering checks;
projects that use the engine run their own configured checks. Windows Server CI
and a clean Windows 11 machine are separate qualification targets. The Windows 11
walkthrough and native client recognition/authentication remain pending; consult
[release verification](docs/release-verification.md) for recorded evidence.

### Create or adopt a project

```sh
# Create a Python project with the GitHub tracker selected.
ai-dlc project init my-project --preset python --tracker github-issues

# Or preview adding AI-DLC to an existing repository.
ai-dlc project adopt --root /path/to/repo --preset generic --tracker github-issues
# Repeat the adoption command with --apply to write the reviewed changes.
```

Use these commands from an installed compatible engine to work on the target
project; cloning and testing the AI-DLC source repository is not a consumer
prerequisite. On native Windows, the supported starter scope is `generic` and
`python`. Other selected or implied modules report their own unsupported or
unqualified status instead of silently changing the selection.

For a newly generated project, initialize Git, run setup, and commit the generated
configuration and lockfile before checking. Checks bind their receipt to `HEAD`:

```sh
cd my-project
git init
ai-dlc project setup
git add .
git commit -m "chore: initialize project"
ai-dlc project check --required
```

During edits, run only the named commands relevant to the change:

```sh
ai-dlc project check --check generated
# Repeat --check to select more configured commands, in the requested order.
ai-dlc project check --check generated --check work-records
```

A successful focused run is local feedback. It cannot replace missing required
outcomes in completion evidence. After integrating the target branch, run
`ai-dlc project check --required` before merge. Teams own the commands and required
IDs in `ai-dlc.toml`; keep their existing test tools and add behavioral acceptance
checks. New Python starters include a standard-library test of their initial
output as well as a syntax check; extend those tests as the application grows.

For an adopted repository, use its existing Git history; run setup and review and
commit the adoption and setup changes before checking. Choose `generic`, `python`,
`node`, or `rust`; optional capabilities include `backend` contract checks and
`frontend` browser smoke tests.

Projects created with the released engine carry its release manifest for their
own bootstrap and CI. Source-generated projects need a published
`bootstrap/release.sh` before release-mode bootstrap. Native projects also need
compatible native release assets, which the historical v0.4.0 release does not
provide. See the
[release guide](docs/runbooks/release-publication.md#install-from-a-release).

### Connect tools and configure the project

The generated `ai-dlc.toml` owns shared policy. For example, these sections select
providers and the repository whose merge/CI evidence must be checked:

```toml
[roles]
specs = "openspec"
tracker = "github-issues"
knowledge = "obsidian"
scm = "github"
deploy = "none"
agent-client = ["claude-code", "codex"]

[scm]
repository = "your-org/your-project"
workflow = "verify.yml"
target_branch = "main"
```

Authenticate the GitHub CLI with access to your repository and Project. Then
preview the connection and apply its saved choices from the project root:

```sh
ai-dlc provider connect github-issues --plan-file .ai-dlc/local/github-project.json
ai-dlc provider connect github-issues --plan-file .ai-dlc/local/github-project.json --apply
ai-dlc agents render --apply
ai-dlc project readiness
```

Connection apply can create or reuse a GitHub Project; inspect the preview first.
Readiness checks local requirements; `doctor` also inspects configured provider
health. See [GitHub setup](docs/github-ticket-setup.md) for existing Projects,
custom statuses, and issues-only mode.

| Configuration | Where it belongs |
| --- | --- |
| Shared providers, setup, checks, gates, agent guidance | Project `ai-dlc.toml`, `.mise.toml`, and repository files |
| Portable tools, personal agent preferences, team subscriptions | Private `ai-dlc-profile.toml` repository |
| Local paths, account selections, credential environment-variable names | Machine binding; use `--machine` where supported |
| Secret values | Password manager, keychain, or injected process environment; never Git |

### Carry preferences and team guidance across machines

Enroll a private profile repository at a reviewed tag or advertised Git ref.
Use the same revision on another machine with its own machine ID:

```sh
ai-dlc machine enroll SOURCE --profile-id my-development --machine-id laptop --ref v1
# Review the plan, then repeat with --apply.
ai-dlc machine status
```

Add reviewed team subscriptions to that profile:

```toml
[[sources]]
id = "engineering"
git = "https://example.com/team/practices.git"
ref = "main"
tags = ["review"]
layout = "ai-dlc" # Use "teamai" for the supported teamai reader.
```

Enrollment locks exact source commits and content digests. `ai-dlc machine sync`
previews newer revisions; `ai-dlc machine sync --apply` activates them. Render the
updated guidance into a project with `ai-dlc agents render --apply --root PATH`.
AI-DLC preserves unrelated client settings and refuses collisions or edits to
owned outputs. See [machine enrollment](docs/runbooks/machine-enrollment.md) for
profile setup, role/tag selection, personal MCP servers, and source restrictions.

## Example workflows

### Take a ticket through delivery

With tracker and SCM connections configured, draft work from an existing issue:

```sh
ai-dlc work new improve-setup --from-issue 42
```

Review `.ai-dlc/work/improve-setup.toml`: set scope and acceptance criteria,
decide whether a specification is required, link it when needed, and set
`reviewed = true`. Then:

```sh
ai-dlc work publish improve-setup
ai-dlc work start improve-setup
# Implement, commit, and update the affected documentation.
ai-dlc project check --required
# If this work requires OpenSpec, finalize it with work archive before review.
# Push the bound branch before opening its PR.
ai-dlc work pr improve-setup
# Push the work-record link commit created by work pr, then review and merge.
```

From a checkout at the merge commit, after CI succeeds, run
`ai-dlc work finish improve-setup`. This validates the required specification,
PR merge, and exact merged-revision CI evidence, plus configured deployment gates.
`work status` is a local inspection, not a fresh tracker read.

### Keep project documents useful

```sh
ai-dlc docs init                  # Preview missing navigation.
ai-dlc docs check                 # Inspect ownership, coverage, and links.
ai-dlc docs search "authentication"
ai-dlc docs review --base origin/main
```

Use reviewed dispositions and `ai-dlc docs gate` to keep documentation current
with a change. Project-document access covers repository files; private vault
access uses separate knowledge tools. The [documentation guide](project-templates/project/docs/documentation-guide.md)
covers review, MCP search/read, and optional Obsidian portals and mounts.

### Start an FDE engagement

```sh
ai-dlc fde scaffold customer-delivery --title "Customer delivery" --dry-run
ai-dlc fde scaffold customer-delivery --title "Customer delivery"
ai-dlc fde check customer-delivery
```

This creates a charter and Discover → Frame → Design → Build → Deploy → Enable →
Expand landing pages under `docs/fde_engagements/`. Stage checks require earlier
exit criteria and recorded evidence before downstream activation. See the
[FDE guide](docs/runbooks/fde-documents.md) for configuration and stage metadata.
Confluence publication and synchronization remain unimplemented.

## Go deeper

- [Architecture](docs/architecture.md) — services, configuration layers, and extension points.
- [Development workflows](docs/development-workflow.md) — discovery, greenfield, brownfield, and design review.
- [Machine enrollment](docs/runbooks/machine-enrollment.md) — profiles, team sources, client configuration, and troubleshooting.
- [Verification status](docs/release-verification.md) — platform/provider evidence and remaining qualification gaps, including Antigravity and hosted execution.
- [Documentation map](docs/index.md) — the full guide index.
