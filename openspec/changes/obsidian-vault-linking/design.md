## Context and decision

PR #28 introduced an opt-in documentation preset and vault link. Review found
unbounded symlink access, unsafe writes, adoption side effects after conflicts,
and a competing specification location. The maintainer authorized repair and a
single-source documentation model on September 8, 2026.

The five pillars are navigation categories, not compulsory duplicate folders:
architecture, decisions, specifications, operations, and reference. A project map
points to existing documents. OpenSpec remains the sole formal specification
home in `openspec/`; `docs/specs/` is never scaffolded. Preserve established
`docs/architecture.md` and `docs/decisions/` locations. New empty categories get
small draft navigation pages, never invented architecture or factual claims.

## Ownership and lifecycle

An optional `docs/catalog.toml` records project-relative canonical paths, stable
IDs, category, owner, lifecycle status, optional review date/interval and source
references. Repository documentation stays authoritative in Git; personal notes
stay in Obsidian; existing team pages stay in Confluence. Sources are references,
not permission to fetch, copy, publish, or refresh content. Derived documents
identify their sources. Superseded entries point to a replacement ID.

A read-only `project docs-check` service (also exposed through MCP) reports missing
catalogued files, duplicate IDs/paths, missing ownership, unknown/overdue review,
exact duplicate Markdown bodies, and uncatalogued documentation. It does not
assert semantic freshness, fuzzy duplicate detection, or automatic cleanup.
The catalog can list canonical OpenSpec files but does not duplicate OpenSpec's
change/task lifecycle. Examples and templates remain distinguishable from active
documents. Invalid metadata reports a structured finding, not a traceback.

## Integration and preservation

The preset is optional and aliases `5-pillar` and `organized`. Preset planning is
part of the shared adoption service: preview includes added paths; conflicts
cause no changes; CLI delegates rather than implementing extra side effects.
Standalone setup uses the same planner. Existing authored files remain intact.
Reject symlinked roots/parents and special files before writing. New files use
exclusive creation through no-follow directory descriptors. Do not delete created
files on failure: preserve partial results and report them for a safe retry.
Machine vault paths never enter tracked project files.

The vault presentation is a normal Markdown project portal containing canonical
file links. It preserves canonical files and personal notes, refuses arbitrary
external traversal, and never treats a directory name as authorization. Directory
mounting and automatic source indexing are deliberately deferred; a portal does
not make repository documents editable inside the main Obsidian vault. Knowledge note and
append retain their original private-vault boundary. A link is not authority to
write repository docs through the personal-note API. No Confluence connector,
site crawler, synchronization engine, or remote publication is introduced.

## Validation

Regressions cover the four reproduced PR defects; existing layouts; no duplicate
spec home; manifest diagnostics with fixed dates; safe retry; preview/apply parity;
CLI/MCP service boundaries; absent machine vault; invalid names; authored links;
and exact preservation of outside/private files. Run all manifest-required checks
and strict OpenSpec validation. Distinguish local filesystem/fixture evidence from
actual Obsidian or Confluence qualification.
