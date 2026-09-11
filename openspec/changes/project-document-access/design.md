# Scoped project-document search and reading

## Context
The approved program separates repository document access from private notes.
Inventory already identifies tracked and nonignored Markdown without following
links. Review already supplies bounded UTF-8 bodies, content digests and line
ranges. Native mounts expose repository files in a client but do not authorize
private-note operations to traverse those mounts.

## Goals / Non-Goals
Provide direct local search/read operations with common scope and evidence
boundaries across CLI and MCP. Reuse inventory and the bounded reader. Do not add
persistent source configuration, change catalog ownership, search private vaults,
fetch links, write documents, or claim semantic review or native qualification.

## Operation contract
- CLI: `project docs-search QUERY` and `project docs-read PATH`, with `--root`,
  repeated `--source`, and `--max-bytes`. Search also accepts `--limit`.
- MCP: `project_docs_search(query, sources=[], max_bytes=64000, limit=20)` and
  `project_docs_read(path, sources=[], max_bytes=64000)`, using the server's selected
  repository. Optional lists must not use mutable Python defaults.
- `max_bytes` is an integer from 1 through 1048576, default 64000. Search applies
  one total body-byte budget across all examined files, including nonmatches.
  `limit` is an integer from 1 through 100, default 20. Boolean values are not
  accepted as integers. A search query is a nonempty literal string.
- Search matches repository-relative paths and body text case-insensitively,
  without regex execution. Visit eligible paths in sorted order and emit at most
  one match per document. Return a bounded excerpt/location for a body match;
  identify path-only matches without inventing a body line. Mark clipped excerpts.
- Read returns the complete body only when it fits the selected budget. Oversized
  files are omitted without reading their bodies. There is no partial-file or
  line-window API in this deliverable.

## Eligibility and source declarations
Default sources are inventory-eligible `.md` files beneath `docs/` and `openspec/`.
Zero to 32 unique additional exact repository-relative Markdown file paths may be
declared through `--source` / `sources` for one call. Declarations add files to the
default scope; they do not replace it or persist after the call. A root document
therefore uses `project docs-read README.md --source README.md`.

Every additional declaration must already be eligible in repository inventory.
Reject absolute paths, traversal, directories, globs, ignored files, unavailable
files and symlinks. A requested read path alone does not declare additional scope.
The default directories may be absent; absence is reported without creating them.
Reject malformed declarations before any document-body reads.

Do not repurpose catalog `sources`, which records external provenance, or widen
catalog entries beyond their existing docs/OpenSpec ownership boundaries. Catalog
presence is not required for access. Inventory may discover root or legacy paths
without authorizing their bodies for a default access call.

## Identity, omissions and filesystem boundary
Normalize and validate the selected repository root consistently before deriving
paths. Linked Git worktrees are valid access roots; the stable-checkout restriction
belongs to mount setup. Preserve no-follow checks before resolving identities.
Use the same canonical root for inventory, eligibility, reads and returned paths.

Return schema version, canonical repository root and effective source declarations.
Each returned document/match includes canonical absolute path, repository-relative
path, source identity distinguishing project documents and `docs`, `openspec` or
explicitly declared scope, and a digest of the actual read bytes. Full reads include
inclusive start/end lines; body search matches identify their source line range.
Canonical absolute paths are runtime results, not shared configuration values.

Expose inventory exclusions and unavailable paths plus per-operation omissions.
State which eligible documents were read and which were not examined because of
budget, result limit, missing/unreadable/unsafe content or decoding failure. A partial
search must not claim exhaustive coverage or an authoritative absence of matches.
Unselected root/legacy bodies remain outside scope and are never opened.

Revalidate path components and file type at the actual read using descriptor-based
no-follow access. Reject symlink substitution, special files and outside paths;
never follow Markdown links or mounted vault paths as new authority. Reuse the
existing bounded UTF-8 reader so binary rejection, byte accounting and digests do
not drift from review packets. Private `Knowledge` remains unchanged.

## Implementation placement and guidance
Add the shared access service in `src/ai_dlc/documentation/document_access.py` and
thin adapters in `cli.py` and `mcp_server.py`. Extract the current review bounded
reader to `document_files.py` if needed, preserving review packet behavior and its
existing tests. Reuse `document_inventory.py` rather than another filesystem scan.

Update canonical and portable tool maps, the documentation guide and relevant
shipped provider/skill guidance, including rendered assets. A harness searches or
reads through project operations, then edits returned canonical repository paths
with ordinary file/Git tools and normal checks. It must not append to a mounted
project document through `knowledge_append` or infer permission from a vault link.

## Verification and rollout
Use disposable repositories and private notes to exercise default/declaration
scope, total budgets, line locations, digests, no-follow reads and CLI/MCP parity.
Run existing review tests after any reader extraction. Verify distribution and a
scoped harness routing scenario separately from native-client qualification.

The new commands are opt-in and do not change existing inventory, catalog review,
portal or private-note defaults. Record documentation-impact dispositions after
content settles. Finalize specifications for review; merge, exact merged-revision
CI receipts and work completion remain subsequent gated lifecycle operations.
