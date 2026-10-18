# Documentation map

Start with [ADR 0001](../decisions/0001-refocus-ai-dlc.md) for the scope freeze,
[product direction](../product-direction.md) for the promise and
[roadmap](../roadmap.md) for what is next. GitHub Issues and the linked
Project own current work status. This index links authoritative documents rather
than reproducing them.

| Question | Canonical entry point |
| --- | --- |
| What is the system? | [Architecture](../architecture.md), with its [terms](../architecture.md#terms) |
| What is in scope? | [Decisions](https://github.com/Sean-Koval/ai-dlc/tree/main/docs/decisions), starting with the [scope freeze](../decisions/0001-refocus-ai-dlc.md); records follow the [decision convention](https://github.com/Sean-Koval/ai-dlc/blob/main/project-templates/project/docs/decisions/README.md) |
| Why is it this way? | Decisions in the relevant [design documents](https://github.com/Sean-Koval/ai-dlc/tree/main/docs/design) and [formal change designs](https://github.com/Sean-Koval/ai-dlc/tree/main/openspec/changes) |
| What must it do? | [OpenSpec](https://github.com/Sean-Koval/ai-dlc/tree/main/openspec) owns formal specifications and change artifacts |
| How do we operate and verify it? | [Get started](../workflows/get-started.md), the [workflow plugin](../workflows/workflow-plugin.md), [release verification](../release-verification.md) and its [verification records](../release-verification.md#verification-records) |
| What changed? | [Changelog](https://github.com/Sean-Koval/ai-dlc/blob/main/CHANGELOG.md) and [migration notes](../migration.md) |
| Where are the details? | [Document ownership](project-documentation.md), [local/shared knowledge](local-and-shared-knowledge.md), and [contracts](https://github.com/Sean-Koval/ai-dlc/tree/main/contracts) |

[Catalog](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/catalog.toml) records selected canonical documents. It is an incremental
inventory, not a claim that every historical plan or verification record has been
reviewed. Run `ai-dlc docs check` to inspect gaps; findings require review,
not automatic deletion. Historical execution plans supply context but do not
supersede current product direction, formal requirements or tracker status.

## Current authority and historical material

Current implementation is Python in `src/ai_dlc/`. Read the architecture together
with canonical [requirements](https://github.com/Sean-Koval/ai-dlc/tree/main/openspec/specs), the [roadmap](../roadmap.md)
and [release limits](../release-verification.md). Active OpenSpec changes are proposals
or work in progress; [archived changes](https://github.com/Sean-Koval/ai-dlc/tree/main/openspec/changes/archive) retain delivery
rationale. A merged specification does not establish live platform qualification.

The [historical executor handoff](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/handoffs/framework-delivery.md) preserves
earlier checkpoints; the roadmap owns current status. The [provider planning handoff](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/planning/provider-toolset-handoff.md),
[historical planning records](https://github.com/Sean-Koval/ai-dlc/tree/main/docs/archive/planning),
and [v4 ledger](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/planning/implementation-v4.md) preserve history; their old
instructions are not current task assignments. The Rust plans, template research and
dated evidence captures pruned in October 2026 remain in git history at tag
`docs-prune-2026-10` (commit `fa867cc`).

The original [September 10 baseline and dispositions](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/verification/documentation-baseline.json)
accounts for every initial docs check finding, including retained historical material,
unknown factual review and illustrative missing paths. It records source hashes,
responsible roles and reasons without copying document bodies. That dated inventory retains the pre-cleanup paths and hashes; it is not a live
inventory. The current catalog and docs check output describe the reorganized tree.
Unknown factual reviews remain visible.

## Documentation workflow delivery (frozen)

[Verification and qualification limits](../verification/documentation-workflow.md)
tracks the new impact/review, personal workspace and SDK guidance behavior.
[The reusable guide](https://github.com/Sean-Koval/ai-dlc/blob/main/project-templates/project/docs/documentation-guide.md) owns
setup and ongoing practice; OpenSpec changes own the delivery requirements.
[The workspace qualification walkthrough](../runbooks/document-workspace-qualification.md)
repeats the messy-project organization and native Obsidian checks.

## FDE engagement documents (frozen)

[The FDE runbook](../runbooks/fde-documents.md) describes the local seven-stage
scaffold and explicit stage checks. FDE is frozen to bug fixes, and Confluence
publication is cut under ADR 0001.

## Placement rules

Current explanations belong in design/, procedures in runbooks/ or workflows/,
and actual verification records in verification/. Formal plans and requirements
stay together in OpenSpec. [The archive](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/README.md) is historical context.
Use Git history for removed scratch reports; do not create another document solely
to report that a change completed. The catalog identifies lifecycle and ownership,
not an assertion that every document has received a factual review.

The [documentation site](https://sean-koval.github.io/ai-dlc/) publishes these
pages from `mkdocs.yml`; add a new durable document to its `nav` beside its catalog
entry. The site excludes `archive/` and raw verification evidence; verification
records are built but listed only from release verification. The home page is
`docs/index.md`; this map is its reference companion.
