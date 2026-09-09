# Project knowledge repair verification

Scope: repair PR #28's document organization and vault boundary behavior. The
[formal change](../../openspec/changes/obsidian-vault-linking/) owns requirements
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
