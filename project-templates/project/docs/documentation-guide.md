# Project documentation ownership and navigation

The project map is `docs/index.md`; the optional inventory is `docs/catalog.toml`.
Neither is a second document store. The five pillars are questions:

| Question | Canonical material | Default location |
| --- | --- | --- |
| What is the system? | Architecture and boundaries | Existing architecture document, otherwise `docs/architecture.md` |
| Why is it this way? | Decisions and trade-offs | Existing decisions or ADR directory, otherwise `docs/decisions/` |
| What must it do? | Formal specifications and change artifacts | `openspec/`, owned by OpenSpec |
| How do we operate it? | Setup, diagnosis and operational procedures | `docs/runbooks/` |
| Where are the details? | Contracts, configuration and reference | `docs/reference/` |

Keep established layouts. A map can point to any canonical project file. Do not
create `docs/specs/` as another specification home or relocate authored documents
just to fit categories. Examples and templates are supporting material, not
claims about the implemented system.

## Setup

From the adopted project:

```sh
ai-dlc project docs-init
ai-dlc project docs-init --apply
ai-dlc project docs-check
```

The first command previews additive paths. `--preset organized` is the default;
`5-pillar` is a compatibility alias. Existing maps and catalogs are preserved.
An existing map needs a deliberate editorial update to include new navigation.
For a new adoption use `--docs-preset organized` on `project init` or `project adopt`.
Preview includes those files; apply refuses known conflicts before writes.
Unexpected concurrent failure retains any created files and reports them; inspect
partial output before retrying, especially after an interrupted adoption.

## Catalog and provenance

Enroll useful authoritative documents incrementally. Use stable IDs and real
responsible roles, not an automatically guessed owner. For example:

```toml
schema = 1

[[documents]]
id = "architecture"
path = "docs/architecture.md"
kind = "architecture"
owner = "repository-maintainers"
status = "active"
# Add reviewed_on and review_after_days only after an actual content review.

[[documents]]
id = "team-guide-summary"
path = "docs/reference/team-guide-summary.md"
kind = "summary"
owner = "project-maintainers"
status = "draft"
sources = [{url = "https://example.atlassian.net/wiki/spaces/TEAM/pages/123", retrieved_on = "2026-09-08", version = "7"}]
```

The second entry is an illustrative shared-summary workflow, not permission to
copy a team page. Private summaries belong in the vault and are not catalogued as
publishable repository documents. Record the actual retrieval date/version for
any selected source. Refresh explicitly and preserve personal annotations.
Use `status = "superseded"` and `superseded_by = "replacement-id"` to direct readers
to a replacement; retain the old rationale/history. Archived documents remain
historical. A modification timestamp or a passing check is not a review.

`docs-check` reads local metadata and Markdown only. It reports unknown/overdue
reviews, missing owners/paths, invalid metadata, unlisted files, exact duplicate
bodies and broken inline local Markdown links. It does not inspect link anchors,
reference-style links, wiki links or remote destinations, determine semantic
accuracy, or decide which duplicates should be deleted. Fenced examples are
excluded from link checking. Templates and examples can be catalogued with those
kinds. OpenSpec retains its own lifecycle checks and is not scanned for catalog
coverage. `--strict` exits nonzero on findings; it is an optional gate.

## Preventing AI document creep

Before writing, search the map, catalog, canonical specs and relevant existing
documents. State the question the proposed document answers and its audience.
Update the existing owner document when that question is already covered. A new
document needs a distinct purpose, an owner, a category, a map/catalog link and
explicit source provenance where applicable. Review affected documentation when
code, contracts, decisions or procedures change. Consolidation is a reviewed edit;
never automatically delete, bulk relocate, rewrite review dates, or copy specs.

## Obsidian and Confluence

```sh
ai-dlc project link-vault --vault /path/to/local/vault --preview
ai-dlc project link-vault --vault /path/to/local/vault
```

Alternatively configure machine `paths.vault`; never put it in shared project
configuration. This creates `Projects/<name>.md`, a portal containing canonical
file links. It copies no document body and is searchable as a normal vault note.
Links open through the OS/client's file handling; they do not mount repository
files as editable notes inside the main vault. OpenSpec links identify its
intended location even before initialization. Personal additions below an unchanged
portal are preserved on repeat setup. Changed source bindings or conflicting
content require a new name or deliberate manual reconciliation, never `--force`.
Legacy directory links are left untouched and require manual inspection. The
private knowledge API does not follow directory symlinks or fetch portal links.

Existing Confluence pages remain team authority; relevant page links and on-demand
reads provide context. An explicitly selected repository-authored team guide may
later have a publication binding with target identity, source digest and expected
remote version. Team edits require reconciliation. Reuse the custom MCP's graph
and grading tools after reviewing its interface. No Confluence connector or
publication implementation is added here. 
