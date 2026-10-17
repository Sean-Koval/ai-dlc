<div class="af-hero" markdown>

<span class="af-eyebrow">Agent factory · Define plane</span>

# Portable development setup and workflows for people and coding agents

<p class="af-lede">AI-DLC owns the local side of delivery: it provisions machines from versioned profiles, authors the shared workflow guidance and skills agents follow, and runs the local work lifecycle from ticket binding to a gated finish. Developers and their coding agents use it in their own repositories.</p>

[Get started](workflows/greenfield.md){ .md-button .md-button--primary } [Suite overview](https://sean-koval.github.io/agent-factory/){ .md-button }

</div>

## What it does

- **Machine provisioning.** Profiles select runtimes, tools and personal agent
  settings; each machine keeps its own paths and account bindings
  ([machine enrollment](runbooks/machine-enrollment.md)).
- **Workflow guidance.** Project instructions, skills, hooks and MCP configuration
  render for supported clients ([workflow tool map](workflows/tool-map.md)).
- **Local work lifecycle.** A work record binds a ticket, branch and specification;
  `ai-dlc work finish` closes the ticket only after merged CI evidence
  ([development workflow](development-workflow.md)).

## How it fits the suite

AI-DLC is the Define plane of the agent factory: it prepares the environment and
workflow that agents run in, while other suite tools run sandboxes and evaluate
harnesses. The [suite architecture](https://sean-koval.github.io/agent-factory/architecture/)
shows the planes and their boundaries.

## Where to go next

Start a new project with the [greenfield workflow](workflows/greenfield.md) or adopt
an existing one with the [brownfield workflow](workflows/brownfield.md). The
[architecture](architecture.md) maps packages and entry points. The documentation
map below links every canonical document.

# AI-DLC documentation map

Start with [product direction](product-direction.md) for the framework's promise
and [roadmap](roadmap.md) for delivery dependencies. GitHub Issues and the linked
Project own current work status. This index links authoritative documents rather
than reproducing them.

| Question | Canonical entry point |
| --- | --- |
| What is the system? | [Architecture](architecture.md) and [proposed delivery design](design/framework-delivery.md) |
| What is in scope? | [Decisions](decisions/), starting with the [scope freeze](decisions/0001-refocus-ai-dlc.md); records follow the [decision convention](../project-templates/project/docs/decisions/README.md) |
| Why is it this way? | Decisions in the relevant [design documents](design/) and [formal change designs](../openspec/changes/) |
| What must it do? | [OpenSpec](../openspec/) owns formal specifications and change artifacts |
| How do we operate and verify it? | [README setup](../README.md), [release verification](release-verification.md) and [verification records](verification/) |
| Where are the details? | [Document ownership](design/project-documentation.md), [local/shared knowledge](design/local-and-shared-knowledge.md), and [contracts](../contracts/) |

[Catalog](catalog.toml) records selected canonical documents. It is an incremental
inventory, not a claim that every historical plan or verification record has been
reviewed. Run `ai-dlc docs check` to inspect gaps; findings require review,
not automatic deletion. Historical execution plans supply context but do not
supersede current product direction, formal requirements or tracker status.

## Current authority and historical material

Current implementation is Python in `src/ai_dlc/`. Read the architecture together
with canonical [requirements](../openspec/specs/), the [reconciled roadmap](roadmap.md)
and [release limits](release-verification.md). Active OpenSpec changes are proposals
or work in progress; [archived changes](../openspec/changes/archive/) retain delivery
rationale. A merged specification does not establish live platform qualification.

The [historical executor handoff](archive/handoffs/framework-delivery.md) preserves
earlier checkpoints; the roadmap owns current status. The [provider planning handoff](archive/planning/provider-toolset-handoff.md),
[historical planning records](archive/planning/),
[v4 ledger](archive/planning/implementation-v4.md) and [Rust Phase 1 plan](archive/legacy/phase-1-rust.md) preserve
history; their old instructions are not current task assignments. Template research
in [template research](archive/research/) and the [historical generation prompt](archive/research/jinja2_template_generation.md)
are supporting material, not current Python implementation contracts.

The original [September 10 baseline and dispositions](archive/verification/documentation-baseline.json)
accounts for every initial docs check finding, including retained historical material,
unknown factual review and illustrative missing paths. It records source hashes,
responsible roles and reasons without copying document bodies. That dated inventory retains the pre-cleanup paths and hashes; it is not a live
inventory. The current catalog and docs check output describe the reorganized tree.
Unknown factual reviews remain visible.

## Documentation workflow delivery

[Verification and qualification limits](verification/documentation-workflow.md)
tracks the new impact/review, personal workspace and SDK guidance behavior.
[The reusable guide](../project-templates/project/docs/documentation-guide.md) owns
setup and ongoing practice; OpenSpec changes own the delivery requirements.
[The workspace qualification walkthrough](runbooks/document-workspace-qualification.md)
repeats the messy-project organization and native Obsidian checks.

## FDE engagement documents

[The FDE runbook](runbooks/fde-documents.md) describes the local seven-stage
scaffold, explicit stage checks and the outstanding Confluence publication boundary.

## Placement rules

Current explanations belong in design/, procedures in runbooks/ or workflows/,
and actual verification records in verification/. Formal plans and requirements
stay together in OpenSpec. [The archive](archive/README.md) is historical context.
Use Git history for removed scratch reports; do not create another document solely
to report that a change completed. The catalog identifies lifecycle and ownership,
not an assertion that every document has received a factual review.

The [documentation site](https://sean-koval.github.io/ai-dlc/) publishes these
pages from `mkdocs.yml`; add a new durable document to its `nav` beside its catalog
entry. The site excludes `archive/` and raw verification evidence.
