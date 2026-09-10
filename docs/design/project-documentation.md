# Project documentation ownership and navigation

AI-DLC organizes references to canonical documents. It does not own a second copy
of specifications, a private-note mirror, or a Confluence synchronization engine.
The maintained reusable instructions are the
[project documentation guide](../../project-templates/project/docs/documentation-guide.md),
which ships into adopted repositories. This design record explains the boundary;
the guide owns setup, catalog examples and the upkeep workflow.

The five pillars are navigation questions: what is the system, why were decisions
made, what behavior is required, how is it operated, and where are the reference
details? Existing project layouts answer those questions without relocation.
OpenSpec owns formal behavior and change artifacts. Repository `docs/` owns durable
architecture, decisions and operational material. A project index and optional
catalog identify canonical paths, ownership, lifecycle and source provenance.

`docs-check` exposes deterministic gaps for review: unknown ownership/review,
missing paths, limited local Markdown-link checks, uncatalogued files and exact
content duplicates. It does not certify accuracy or automatically consolidate
content. Review dates represent an actual review, not filesystem timestamps.
OpenSpec remains responsible for its own artifact lifecycle.

An Obsidian portal is a machine-local Markdown note linking to canonical repository
files. It copies no document body and does not mount repository files as editable
notes inside the main vault. Personal note operations retain their original vault
boundary. Existing project directory links are preserved for manual inspection.
No direct Obsidian client qualification is claimed by filesystem tests.

Existing team pages remain authoritative in Confluence; relevant page links and
on-demand reads provide context. Later, an explicitly selected repository-authored
team guide can have a publication binding with source digest, target identity and
expected remote version. Team edits require reconciliation. Reuse the custom
Confluence MCP after inspecting its interface. See
[local and shared knowledge](local-and-shared-knowledge.md) for that workflow.

The formal requirements and repair rationale are in the
[OpenSpec change](../../openspec/changes/archive/2026-09-10-obsidian-vault-linking/).

## Evidence and private-workspace extensions

The approved documentation program adds Git impact inspection, explicit
content-bound dispositions, scoped harness review packets and citation validation.
These services coordinate review; they cannot infer semantic accuracy. A linked
Obsidian workspace adds personal navigation and templates while canonical document
bodies remain in Git. SDK workflow bundles may carry declared references and exact
version applicability, preserving pinned ownership and independent company authority.

The reusable documentation guide linked above owns commands and editorial process.
Formal behavior remains in the corresponding OpenSpec changes; verified execution
and remaining live qualification are recorded in
[documentation workflow verification](../verification/documentation-workflow.md).
