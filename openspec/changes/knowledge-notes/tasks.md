## 1. Schema and learnings (#206)

- [x] 1.1 Add `knowledge_notes` with the `KnowledgeNote` model, generate `contracts/knowledge-note.schema.json` and add its drift check.
- [x] 1.2 Generate or fill learning frontmatter in `work finish` (CLI and MCP) with gate provenance and an explicit author; journal the final note.
- [x] 1.3 Make recall skip expired notes and flag stale ones; prefix stale notes in the session hook.
- [x] 1.4 Add `ai-dlc knowledge check --vault PATH`.
- [x] 1.5 Update the `handoff` and `day-end` skills and relock digests.

## 2. Decision records (#207)

- [x] 2.1 Rewrite the ADR template and the template's decisions README; add the documentation-guide section.
- [x] 2.2 Validate decision frontmatter and the supersede-not-edit rule in `docs check`.
- [x] 2.3 Back-fill ADR 0001 with frontmatter.

## 3. Tests, documentation and delivery

- [x] 3.1 Test generation, preservation, idempotency, conflict, recall, `knowledge check`, template output, schema errors and the accepted-record rule.
- [x] 3.2 Update the knowledge and documentation designs, tool map, index, contracts README and catalog; record content-bound dispositions.
- [x] 3.3 Run the required checks.

## Subsequent delivery gates

Archive this change on its delivery branch with `ai-dlc work archive`, update from
the target branch and rerun required checks immediately before merge, and finish
through `ai-dlc work finish` against the merged revision.
