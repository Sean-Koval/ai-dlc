<div class="af-hero" markdown>

<span class="af-eyebrow">Agent factory · Define plane</span>

# One pinned setup, one workflow, and a finish that needs merged evidence

<p class="af-lede">Every developer's machine is set up differently, and every coding agent closes tickets on its own idea of "done". AI-DLC gives a team one pinned machine profile, one workflow its agents follow in Claude Code or Codex, and a <code>work finish</code> that closes a ticket only when the merged commit has a passing CI receipt.</p>

[Get started](workflows/get-started.md){ .md-button .md-button--primary } [Suite overview](https://sean-koval.github.io/agent-factory/){ .md-button }

</div>

## See it work

Enroll a machine from a pinned profile (preview, apply, status):

![A terminal session: ai-dlc machine enroll previews the example profile's modules and credentials, applies it to a machine binding, and machine status reports the pinned profile commit and one unbound credential](assets/front/enroll.svg)

Take one piece of work from a reviewed record to a closed ticket. GitHub is played by a
local stand-in ([`demo_provider.py`](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/assets/front/demo_provider.py))
that speaks the provider contract, so the gates check a real local merge and the receipt
`project check` wrote:

![A terminal session: work new creates a record, a person marks it reviewed, work publish opens issue 42, work start creates the branch, work pr opens pull request 43, the branch merges, project check passes and writes a receipt, and work finish verifies the merge and CI receipt and closes the issue](assets/front/work.svg)

## What it looks like

The workflow plugin's skills, as Claude Code lists them, and the checks a project requires:

![Claude Code plugin details for ai-dlc-workflow: eleven skills and three hooks](assets/front/plugin-skills.svg)

![ai-dlc project check --required in the demo project: the required checks, a clean tree, and each check passing with exit code 0](assets/front/project-check.svg)

## Where it sits

--8<-- "docs/assets/front/suite.svg"

AI-DLC does not run agents in the cloud or judge harnesses: hangar renders and runs
sandboxes, flightdeck evaluates, and AI-DLC authors the one optional plugin they pin.

## Use cases

- **A new engineer is productive on day one.** They enroll their laptop from the team's
  profile at a reviewed tag: the same runtimes, Claude Code and Codex settings and named
  credentials as everyone else, with their own paths and accounts. `machine status` shows
  what drifted later.
- **An agent cannot declare victory early.** A developer and their agent take an issue
  through `work start` and `work pr`; `work finish` refuses until the PR is merged into the
  target branch and that merge commit has a passing CI receipt, then closes the issue.
- **A team measures whether its workflow helps.** The maintainer publishes the workflow
  plugin into the team harness, off in `stable` and on in `candidate`, and flightdeck
  compares agent runs with and without it.

## Quickstart

Needs git and curl on macOS or Linux (native Windows is not supported yet). Five commands,
from a fresh machine to a project whose required checks pass:

```sh
git clone https://github.com/Sean-Koval/ai-dlc.git && cd ai-dlc
sh scripts/bootstrap.sh --source
export PATH="$HOME/.local/share/ai-dlc/bootstrap/bin:$PATH"
ai-dlc project init ~/demo-app && cd ~/demo-app && git init -q && ai-dlc project setup --root .
git add -A && git commit -qm "chore: initialize with ai-dlc" && ai-dlc project check --required
```

[Get started](workflows/get-started.md) covers existing work repositories, GitHub, profiles and
contributing to the engine.

## Features

| Feature | What you get | Read more |
| --- | --- | --- |
| Machine enrollment | Versioned profiles pin runtimes, tools, agent clients and named credentials; each machine keeps its own paths and accounts | [Machine enrollment](runbooks/machine-enrollment.md) |
| Project scaffolding | `project init` / `project adopt` for generic, Python, Node or Rust repositories, with setup steps and required checks | [Get started](workflows/get-started.md) |
| Workflow plugin | Guidance, ten team skills and CLI-optional safety hooks for Claude Code, with a Codex form; off by default | [Plugin README](https://github.com/Sean-Koval/ai-dlc/blob/main/plugins/ai-dlc-workflow/README.md) |
| Work lifecycle | Reviewed work records bind an issue, branch, specification and PR; `work finish` gates on the merge and its CI receipt | [Development workflow](development-workflow.md) |
| Receipts | `project check --required` runs the team's checks and writes a receipt bound to the commit | [Release verification](release-verification.md) |
| Documentation upkeep | Catalog, impact review, dispositions and a docs gate; decision records with knowledge-note frontmatter | [Project documentation](design/project-documentation.md) |
| Agent access | `ai-dlc mcp serve` exposes reviewed work, documentation and knowledge tools to agents | [Workflow tool map](workflows/tool-map.md) |
| Providers | GitHub Issues + Projects (default), Jira Cloud, OpenSpec, Obsidian | [Architecture](architecture.md) |

# AI-DLC documentation map

Start with [product direction](product-direction.md) for the framework's promise
and [roadmap](roadmap.md) for delivery dependencies. GitHub Issues and the linked
Project own current work status. This index links authoritative documents rather
than reproducing them.

| Question | Canonical entry point |
| --- | --- |
| What is the system? | [Architecture](architecture.md) and [proposed delivery design](design/framework-delivery.md) |
| What is in scope? | [Decisions](https://github.com/Sean-Koval/ai-dlc/tree/main/docs/decisions), starting with the [scope freeze](decisions/0001-refocus-ai-dlc.md) |
| Why is it this way? | Decisions in the relevant [design documents](https://github.com/Sean-Koval/ai-dlc/tree/main/docs/design) and [formal change designs](https://github.com/Sean-Koval/ai-dlc/tree/main/openspec/changes) |
| What must it do? | [OpenSpec](https://github.com/Sean-Koval/ai-dlc/tree/main/openspec) owns formal specifications and change artifacts |
| How do we operate and verify it? | [Get started](workflows/get-started.md), [release verification](release-verification.md) and [verification records](https://github.com/Sean-Koval/ai-dlc/tree/main/docs/verification) |
| Where are the details? | [Document ownership](design/project-documentation.md), [local/shared knowledge](design/local-and-shared-knowledge.md), and [contracts](https://github.com/Sean-Koval/ai-dlc/tree/main/contracts) |

[Catalog](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/catalog.toml) records selected canonical documents. It is an incremental
inventory, not a claim that every historical plan or verification record has been
reviewed. Run `ai-dlc docs check` to inspect gaps; findings require review,
not automatic deletion. Historical execution plans supply context but do not
supersede current product direction, formal requirements or tracker status.

## Current authority and historical material

Current implementation is Python in `src/ai_dlc/`. Read the architecture together
with canonical [requirements](https://github.com/Sean-Koval/ai-dlc/tree/main/openspec/specs), the [reconciled roadmap](roadmap.md)
and [release limits](release-verification.md). Active OpenSpec changes are proposals
or work in progress; [archived changes](https://github.com/Sean-Koval/ai-dlc/tree/main/openspec/changes/archive) retain delivery
rationale. A merged specification does not establish live platform qualification.

The [historical executor handoff](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/handoffs/framework-delivery.md) preserves
earlier checkpoints; the roadmap owns current status. The [provider planning handoff](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/planning/provider-toolset-handoff.md),
[historical planning records](https://github.com/Sean-Koval/ai-dlc/tree/main/docs/archive/planning),
[v4 ledger](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/planning/implementation-v4.md) and [Rust Phase 1 plan](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/legacy/phase-1-rust.md) preserve
history; their old instructions are not current task assignments. Template research
in [template research](https://github.com/Sean-Koval/ai-dlc/tree/main/docs/archive/research) and the [historical generation prompt](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/research/jinja2_template_generation.md)
are supporting material, not current Python implementation contracts.

The original [September 10 baseline and dispositions](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/verification/documentation-baseline.json)
accounts for every initial docs check finding, including retained historical material,
unknown factual review and illustrative missing paths. It records source hashes,
responsible roles and reasons without copying document bodies. That dated inventory retains the pre-cleanup paths and hashes; it is not a live
inventory. The current catalog and docs check output describe the reorganized tree.
Unknown factual reviews remain visible.

## Documentation workflow delivery

[Verification and qualification limits](verification/documentation-workflow.md)
tracks the new impact/review, personal workspace and SDK guidance behavior.
[The reusable guide](https://github.com/Sean-Koval/ai-dlc/blob/main/project-templates/project/docs/documentation-guide.md) owns
setup and ongoing practice; OpenSpec changes own the delivery requirements.
[The workspace qualification walkthrough](runbooks/document-workspace-qualification.md)
repeats the messy-project organization and native Obsidian checks.

## FDE engagement documents

[The FDE runbook](runbooks/fde-documents.md) describes the local seven-stage
scaffold, explicit stage checks and the outstanding Confluence publication boundary.

## Placement rules

Current explanations belong in design/, procedures in runbooks/ or workflows/,
and actual verification records in verification/. Formal plans and requirements
stay together in OpenSpec. [The archive](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/README.md) is historical context.
Use Git history for removed scratch reports; do not create another document solely
to report that a change completed. The catalog identifies lifecycle and ownership,
not an assertion that every document has received a factual review.

The [documentation site](https://sean-koval.github.io/ai-dlc/) publishes these
pages from `mkdocs.yml`; add a new durable document to its `nav` beside its catalog
entry. The site excludes `archive/` and raw verification evidence.
