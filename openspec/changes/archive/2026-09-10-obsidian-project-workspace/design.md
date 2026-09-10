# Organize linked project workspaces in Obsidian

## Decisions

Use existing Python application services for shared CLI/MCP behavior. OpenSpec owns proposal, design, behavioral specification and tasks. Repository docs own durable explanations; Obsidian owns private continuity. Existing harnesses perform semantic reasoning. Source citations are evidence, not automatic authority or permission to fetch.

## Scope and verification

- OW-01: Linked workspace navigation. Verify through the linked scenario and observable negative cases.
- OW-02: Preserving workspace upgrades. Verify through the linked scenario and observable negative cases.
- OW-03: Selective personal continuity. Verify through the linked scenario and observable negative cases.

Preserve authored content and filesystem boundaries. No automatic deletion, remote publication or freshness certification. Required checks and independent review precede integration. Live qualification is distinct from fixtures.

## Additive upgrades and public interface

`setup_workspace(root, vault=None, name=None, bases=False, apply=False)` serves CLI `project workspace-init` and read-only MCP `project_workspace_preview`. Existing `Projects/<name>.md` remains the canonical-file portal with all its annotations. An additive `Projects/<name>-workspace.md` organizes private focus, questions, daily notes and learnings, with YAML `note_kind`, `project`, `status`, `source`. This is private navigation, not another specification home. New setup creates both if absent. No existing note body is rewritten: authored changes are preserved or reported as conflicts.

Reusable daily/question/learning templates live under `AI-DLC/Templates/`. Optional `AI-DLC/Views/` Bases files organize project properties without plugins or body copies. Core backlinks and Markdown remain usable without Bases. Each note's project property links its workspace; evidence source links and interpretation are separate.

All destinations preflight before writes and use exclusive no-follow creation. Exact existing templates/views are reused; personal appended text on portals/workspaces remains unchanged. Unexpected failures retain and report created output, never pathname-delete. Missing repository fails before writes; missing index/OpenSpec is explicitly reported for setup, not described as existing knowledge. Changed bindings need explicit reconciliation or another project name.

## Delivery evidence

Scoped and integrated independent review approved. All six required local checks passed with 2022 tests and8 skips before archival-only metadata finalization. See docs/verification/documentation-workflow.md for exact scope and live qualification limits.
