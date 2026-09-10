# Organization design

## Authority

AGENTS.md owns repository context; CLAUDE.md imports it. OpenSpec owns formal
change artifacts. Current docs remain task-oriented; superseded plans and research
move to docs/archive with clear historical labels and original Git provenance.
Immutable verification snapshots retain their original paths and hashes as evidence.

## Python boundaries

Keep public CLI/MCP/conformance entry points, configuration, contracts and shared
filesystem utilities at package root. Group documentation, harness rendering,
project setup, work lifecycle, machine enrollment, verification support and legacy
compatibility into explicit subpackages. Provider adapters remain in providers.
Update imports and dynamic references, including tests and asset lookup paths.
Do not equate absence of static imports with dead code: subprocess entry points
and packaged compatibility assets are active.

## Prevention

A repository layout check rejects unexpected root Markdown, tool-specific scratch
folders and new flat Python modules. The existing documentation gate rejects
broken current document links. Historical
snapshots are retained as historical evidence, not silently rewritten as fresh.
The existing document-impact gate records the reviewed relocation and mappings.

## Claude compatibility

An absent or exact plain CLAUDE.md is rendered as @AGENTS.md followed by newline.
Existing authored text and managed sections keep their ownership/conflict behavior.
The repository's obsolete authored Rust context is explicitly removed by this change.
