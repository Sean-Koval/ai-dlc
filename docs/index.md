# AI-DLC documentation map

Start with [product direction](product-direction.md) for the framework's promise
and [roadmap](roadmap.md) for delivery dependencies. GitHub Issues and the linked
Project own current work status. This index links authoritative documents rather
than reproducing them.

| Question | Canonical entry point |
| --- | --- |
| What is the system? | [Architecture](architecture.md) and [proposed delivery design](design/framework-delivery.md) |
| Why is it this way? | Decisions in the relevant [design documents](design/) and [formal change designs](../openspec/changes/) |
| What must it do? | [OpenSpec](../openspec/) owns formal specifications and change artifacts |
| How do we operate and verify it? | [README setup](../README.md), [release verification](release-verification.md) and [verification records](verification/) |
| Where are the details? | [Document ownership](design/project-documentation.md), [local/shared knowledge](design/local-and-shared-knowledge.md), and [contracts](../contracts/) |

[Catalog](catalog.toml) records selected canonical documents. It is an incremental
inventory, not a claim that every historical plan or verification record has been
reviewed. Run `ai-dlc project docs-check` to inspect gaps; findings require review,
not automatic deletion. Historical execution plans supply context but do not
supersede current product direction, formal requirements or tracker status.

## Current authority and historical material

Current implementation is Python in `src/ai_dlc/`. Read the architecture together
with canonical [requirements](../openspec/specs/), the [reconciled roadmap](roadmap.md)
and [release limits](release-verification.md). Active OpenSpec changes are proposals
or work in progress; [archived changes](../openspec/changes/archive/) retain delivery
rationale. A merged specification does not establish live platform qualification.

The [executor handoff](handoffs/framework-delivery.md) leads with current status and
labels older checkpoints. The [provider planning handoff](archive/planning/provider-toolset-handoff.md),
[historical planning records](archive/planning/),
[v4 ledger](archive/planning/implementation-v4.md) and [Rust Phase 1 plan](archive/legacy/phase-1-rust.md) preserve
history; their old instructions are not current task assignments. Template research
in [template research](archive/research/) and the [historical generation prompt](archive/research/jinja2_template_generation.md)
are supporting material, not current Python implementation contracts.

The original [September 10 baseline and dispositions](verification/documentation-baseline.json)
accounts for every initial docs-check finding, including retained historical material,
unknown factual review and illustrative missing paths. It records source hashes,
responsible roles and reasons without copying document bodies. That dated inventory retains the pre-cleanup paths and hashes; it is not a live
inventory. The current catalog and docs-check output describe the reorganized tree.
Unknown factual reviews remain visible.

## Documentation workflow delivery

[Verification and qualification limits](verification/documentation-workflow.md)
tracks the new impact/review, personal workspace and SDK guidance behavior.
[The reusable guide](../project-templates/project/docs/documentation-guide.md) owns
setup and ongoing practice; OpenSpec changes own the delivery requirements.
[The workspace qualification walkthrough](runbooks/document-workspace-qualification.md)
repeats the messy-project organization and native Obsidian checks.

## Placement rules

Current explanations belong in design/, procedures in runbooks/ or workflows/,
and actual verification records in verification/. Formal plans and requirements
stay together in OpenSpec. [The archive](archive/README.md) is historical context.
Use Git history for removed scratch reports; do not create another document solely
to report that a change completed. The catalog identifies lifecycle and ownership,
not an assertion that every document has received a factual review.
