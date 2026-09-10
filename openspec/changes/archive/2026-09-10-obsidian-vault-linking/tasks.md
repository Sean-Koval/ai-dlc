# Project Knowledge Repair Tasks

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Organize canonical project documentation and link it to private knowledge without duplicate specifications or implicit synchronization.

**Architecture:** Shared documentation planning and checking services; OpenSpec owns formal requirements; vault presentation uses machine-local bindings. Preserve authored files and keep private note writes inside the vault.

**Tech Stack:** Python, Typer, existing stdio MCP, TOML and Markdown.

**Spec:** design.md and specs/obsidian-vault-linking/spec.md (relative to this archived change).

## Global constraints

- No new content store, connector, crawler or semantic index.
- No automatic publication, deletion, migration or freshness claims.
- No vault paths in tracked project configuration.
- Existing authored documents and OpenSpec paths remain canonical.

## Task 1: Shared preset planning and safe creation

Files: src/ai_dlc/document_files.py, src/ai_dlc/moc.py, src/ai_dlc/templates.py, src/ai_dlc/cli.py, tests/test_vault_link.py, tests/test_project_documents.py.

- [x] Write regressions using real temporary projects for nested symlink escape and CLI adoption conflict. Assert outside bytes unchanged and no docs on conflict.
- [x] Run focused tests; record expected failures before implementation.
- [x] Implement `plan_documents(root: Path, project_name: str) -> dict[str, bytes]`; preserve authored paths and prefer existing category locations. Generate navigation, catalog and only missing category guides.
- [x] Fold planned files into adoption's stage and returned path list; validate preset before mutation. Remove CLI-only scaffolding.
- [x] Implement no-follow descriptor-based exclusive file creation for new standalone documents. Preserve any partial output with an actionable error; never unlink an authored replacement.
- [x] Run focused tests including repeated apply, unknown preset, and preview side effects.

## Task 2: Catalog inspection

Files: src/ai_dlc/documents.py, src/ai_dlc/cli.py, src/ai_dlc/mcp_server.py, tests/test_project_documents.py.

- [x] Write table-driven fixtures: missing source, duplicate identity/path, unknown owner/review, stale review at a fixed date, uncatalogued and byte-identical files, superseded reference, malformed TOML.
- [x] Assert `check_documents(root, today=date(2026, 9, 8))` reports expected codes and never mutates or fetches sources.
- [x] Implement schema validation and bounded local inspection. Share the service between CLI and MCP. Return findings and an honest freshness limitation.
- [x] Verify CLI exit behavior and MCP exposure through their actual interfaces.

## Task 3: Vault presentation repair

Files: src/ai_dlc/vault_link.py, src/ai_dlc/knowledge.py, src/ai_dlc/files.py, tests/test_vault_link.py, tests/test_knowledge.py.

- [x] Adopt the stated default: a local Markdown portal with canonical file links; directory mounting is deferred.
- [x] Reproduce invalid names, symlinked parents, arbitrary project traversal, conflicting authored paths and failed-link preflight.
- [x] Restore strict `inside` and private-note write boundaries; implement only the explicitly selected link mechanism.
- [x] Verify portable config stays free of local bindings, existing vault content is preserved, and retries are safe.

## Task 4: Delivery and review

Files: docs/design/local-and-shared-knowledge.md, project-templates/project/docs/, README.md and OpenSpec change artifacts.

- [x] Explain ownership, provenance, explicit review, searching before creation, supersession and selective team sources in one reusable guide.
- [x] Add project navigation without relocating existing documentation or copying specs. Remove incidental Beads files from this PR.
- [x] Run `ai-dlc project check --required` against the final repaired code; all five checks pass. Strict OpenSpec validation passes for all 24 items.
- [x] Review the complete diff and reconcile tasks with actual evidence; do not claim live client qualification or finish before merge gates.
