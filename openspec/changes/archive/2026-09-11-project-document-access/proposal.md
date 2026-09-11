# Provide scoped project-document discovery and reading to harnesses

## Why
Repository inventory discovers document paths and review packets provide selected
review evidence. Harnesses also need a direct, bounded way to search and read
project documentation without routing mounted repository files through the
private-note API. Root and legacy documents should be eligible only when explicitly
selected, rather than by broadening private knowledge or catalog ownership rules.

## What Changes
- Add shared `project docs-search` / `project_docs_search` and `project docs-read` /
  `project_docs_read` operations. Default scope is inventory-eligible Markdown in
  `docs/` and `openspec/` in the selected repository.
- Repeated CLI `--source` arguments or MCP `sources` declare exact additional
  inventory-eligible Markdown files for that call. No new configuration or catalog
  schema is introduced.
- Return canonical repository and document paths, source identity, content digests
  and line locations. Enforce aggregate search/read budgets and expose omissions
  instead of presenting partial searches as complete.
- Update generated guidance to distinguish project-document access from private
  knowledge and route edits through ordinary repository tools and verification.

## Capabilities
### New Capabilities
- project-document-access: Scoped project-document search and reading for harnesses

## Impact
Shared Python documentation services, thin CLI/MCP adapters, focused boundary and
parity tests, and canonical/portable guidance. The inventory and bounded review
reader are reused; private `Knowledge` behavior and catalog enrollment constraints
remain unchanged. Depends on harness-document-organization (#39) and
obsidian-native-project-mounts (#40). Related #32/#34 qualification remains
independent. No vault traversal, editing service, index daemon, Jira integration,
synchronization or remote publication.
