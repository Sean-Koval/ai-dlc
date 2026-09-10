# Project knowledge repair verification

Scope: repair PR #28's document organization and vault boundary behavior. The
[formal change](../../openspec/changes/archive/2026-09-10-obsidian-vault-linking/) owns requirements
and the execution checklist. The source guide lives in the project template and
is linked from the design record rather than copied into another maintained guide.

## Observed evidence

- TDD first reproduced unsafe scaffolding and adoption conflict side effects;
  new catalog/service tests failed before their implementations existed.
- Restored private knowledge boundaries reject arbitrary and nested project
  symlinks. Portal tests verify canonical links without copied bodies, safe names,
  authored-note preservation, idempotence, legacy mount refusal and read-only preview.
- Adoption tests exercise real Copier templates, document preview/apply parity,
  missing-vault preflight and authored files inserted after planning. Exclusive
  creation retains partial output rather than deleting pathname replacements.
- Independent review found symlink-root preflight, empty normalized paths,
  malformed URL handling and existing architecture-directory selection issues.
  Each was reproduced before repair. Follow-up review found ordinary-file/FIFO
  parent conflicts; three further regressions confirmed those before repair.
- A disposable default-template project with GitHub, Claude and Antigravity selected
  initialized successfully with an organized map and local portal. No `docs/specs/`
  was created and its new map had no broken local links. This is setup evidence,
  not actual client recognition or authentication.
- Final focused regression suite: 46 passed. Independent reviewer approved the
  repaired implementation with no remaining actionable findings.
- Strict OpenSpec validation: 24 items passed, zero failed.

Final prepared-environment manifest run passed all five required checks: generated,
format, lint, types and tests. Test result: 1943 passed, 8 skipped in 318.60s (0:05:18).
The earlier run overlapped the review fixes and is not used as final-candidate evidence.

## Limits and disposition

Filesystem and CLI/MCP fixtures are local evidence. This cycle did not open an
actual Obsidian vault, exercise installed native clients, inspect the custom
Confluence server, publish pages or synchronize content. Canonical file links
use the OS/client's file handling; they do not mount repository files as editable
notes inside the main vault. These are explicit product boundaries, not claims
of native Obsidian qualification.

The initial repository inventory exposes uncatalogued historical docs and stale
links. It is a review queue, not authorization for bulk rewriting, new review
dates, deletions or an assertion of semantic freshness. Existing authored files
and legacy mounts are preserved. No package publication, spec archive or gated
work finish is part of this repair before merge and exact merged-CI evidence.

## September 10 delivery reconciliation

Read-only GitHub inspection confirmed PR28 is MERGED at
`74b90c67f9f0b29a0a4bae688ea6b670608aea18`, with head
`6c0a732d127a6bb610fe66057965701e9c1cbf3b`. Its five Verify checks succeeded in
[run 34309239909](https://github.com/Sean-Koval/ai-dlc/actions/runs/34309239909).
These are PR-head checks, not independently verified exact merged-revision receipts.
No gated work finish is claimed by this editorial reconciliation.

The following source/fixture reconciliation was performed against the merged source
in this checkout. A fresh focused run of `tests/test_project_documents.py`,
`tests/test_vault_link.py` and `tests/test_knowledge.py` passed all 46 tests.

| Requirement | Delivered source and evidence | Boundary |
| --- | --- | --- |
| DK-01 | `src/ai_dlc/moc.py:plan_documents`; existing layout and missing-spec navigation regressions | Navigation preserves canonical files; it does not invent architecture |
| DK-02 | `src/ai_dlc/templates.py:adopt`, `src/ai_dlc/document_files.py`; conflict, preview parity and concurrent authored-file regressions | Exclusive creation retains partial output; no implicit cleanup |
| DK-03 | `src/ai_dlc/vault_link.py`; safe name, authored portal, missing vault and legacy-link regressions | Markdown portal only; actual Obsidian editing is unqualified |
| DK-04 | `src/ai_dlc/knowledge.py` and `src/ai_dlc/files.py`; arbitrary/nested symlink regressions | Private-note boundary; linked source bodies are not fetched |
| DK-05 | `src/ai_dlc/documents.py`; catalog provenance, ownership, supersession and malformed metadata cases | Metadata is explicit; source URLs grant no publication authority |
| DK-06 | `src/ai_dlc/documents.py`, CLI and MCP interfaces; shared-result and read-only diagnostics regressions | No semantic freshness, remote source checks or automatic repair |
| DK-07 | `project-templates/project/docs/documentation-guide.md` and generated map in `src/ai_dlc/moc.py` | Upkeep guidance preserves separate tracker, specification and publication authority |

`openspec archive obsidian-vault-linking --yes` validated and archived the delivered
change as `2026-09-10-obsidian-vault-linking`, creating the canonical
[DK specification](../../openspec/specs/obsidian-vault-linking/spec.md).
The work record now points to that archive. Earlier pre-merge statements above
remain historical evidence. Source inspection and these regressions do not add
live Obsidian, Confluence, native-client, or platform qualification.
