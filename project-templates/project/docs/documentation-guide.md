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

## Organizing an existing repository

For an outcome such as “organize the scattered project docs,” use the shipped
`document-organize` skill. Discovery starts before catalog enrollment:

```sh
ai-dlc project docs-inventory
ai-dlc project docs-review --base HEAD --source inventory --path README.md --path legacy/setup.md
```

Select actual paths returned by inventory. It lists tracked and nonignored `.md`
files throughout the repository, including root and legacy directories, without
reading document bodies. Git-ignored paths, Git metadata and nested repositories
are excluded explicitly; symlinks are never followed, and missing/inaccessible
paths remain reported. Tracked documents remain eligible even if ignore patterns
match them. This is a local working-tree inventory, not a claim of content review.

`docs-review` defaults to `--source catalog` for existing callers. Explicit
`--source inventory` permits 1–32 selected inventory documents without creating a
catalog. Existing catalog mappings still supply local evidence, but unselected
inventory documents remain outside review scope. Uncatalogued documents have no
inferred code mappings: select related documents deliberately and inspect relevant
code/spec sources separately, stating which evidence is outside the packet. The
same total byte budget, hashes, exact citations and stale-source checks apply.
A changed inventory scope also requires a fresh packet. Its inventory field retains
excluded and inaccessible paths; omitted bodies must remain unreviewed.

Review purpose, audience, claims and unique content before proposing a destination
or consolidation. Present a concrete source-to-destination plan with retain,
revise, consolidate or archive decisions and reasons. Apply reviewed decisions as
ordinary Git moves and edits within the authorized task. Preserve unique rationale
and useful summaries; label retained history and point to its successor. Keep
OpenSpec requirements and change records under OpenSpec ownership. Repair inbound
and outbound links, including relative paths whose base changed, then update the
map and catalog for canonical documents. Keep a useful root entry point when it
serves repository readers. Do not create empty folders as a substitute for cleanup.

Inspect the resulting Git diff, run document diagnostics and required project
checks, and record reviewed impact dispositions after content settles. Check
reference-style links, anchors and wiki links separately where the local checker
cannot verify them. Report actual changes and remaining omissions. An inventory,
a recommendation report or additive `docs-init` output alone does not complete an
authorized organization request.

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

### Opt in to native project folders

```sh
ai-dlc project link-vault --mode mount --vault /path/to/local/vault --preview
ai-dlc project link-vault --mode mount --vault /path/to/local/vault
```

Run from the stable Git checkout root, with existing `docs/` and ignored
`.ai-dlc/local/`. Linked Git worktrees cannot supply mount sources. Preview reports
exact source and destination paths, each action, missing sources, and the local
binding content and path. Omitting `--preview` explicitly applies setup, consistent
with portal linking. The MCP `project_vault_mount_preview` provides the same
read-only mount inspection.

Mount mode creates sibling directory symlinks at `Projects/<name>/docs` and,
when initialized, `Projects/<name>/openspec`. Missing OpenSpec is reported without
creation. It exposes the original repository files for native client editing;
normal Git review and specification ownership still apply. Initialize documentation
separately; mount mode does not scaffold it. Existing portals and nearby personal
notes remain untouched.

Bindings live only in ignored `.ai-dlc/local/vault-mounts/<destination-hash>.json`;
they identify the stable checkout, vault and project name. Shared configuration
never contains these machine paths. Repeating setup preserves matching owned
mounts. Matching unowned links require `--adopt`; conflicting paths are never
replaced. Sources cannot contain nested symlinks or special files. Vault/project
overlap, loops and overlapping targets of existing vault links are rejected.
Unexpected failures report retained output, including the binding and completed
links; inspect it and retry without deleting authored content.

Filesystem tests establish exercised creation, editing and preservation behavior.
They do not qualify Obsidian indexing, external-editor refresh, file watching,
Git tooling, Sync or another client/platform. Qualify those on the intended client
before relying on them. Native mounts do not enable synchronization, publication
or symlink traversal through the private knowledge API.

Existing Confluence pages remain team authority; relevant page links and on-demand
reads provide context. An explicitly selected repository-authored team guide may
later have a publication binding with target identity, source digest and expected
remote version. Team edits require reconciliation. Reuse the custom MCP's graph
and grading tools after reviewing its interface. No Confluence connector or
publication implementation is added here. 

## Review affected documentation during development

Before implementation, choose the Git comparison base and inspect affected sources:

```sh
ai-dlc project docs-impact --base origin/main
```

Catalog entries may declare `code_paths`, `requirements`, and `verification_paths`
as project-relative paths or globs. These relationships identify review candidates;
they cannot prove that every affected document was found. Unmapped changes remain
explicit and need a disposition. A requirement reference points to its canonical
OpenSpec file, not another copy of its text.

Read existing explanations before creating a new document. State the audience and
question being answered. Use the narrowest canonical owner document that serves
that purpose. Introduce concrete behavior, relevant examples, limitations and
operational consequences; remove generic claims and repeated introductions.
A short document can be complete, while a long one can still omit the essential
procedure. Do not use word counts or an LLM grade as a quality guarantee.

After reviewing the implementation and documentation, prepare decisions as JSON:

```json
[
  {
    "target": "docs/reference/api.md",
    "outcome": "updated",
    "reason": "Updated retry guidance against the changed request loop and retry test."
  },
  {
    "target": "tests/test_retry.py",
    "outcome": "no-impact",
    "reason": "Test-only parameterization; the public retry contract is unchanged."
  }
]
```

Use actual targets from the impact report. Every affected document and unmapped
file requires one disposition: `updated`, `reviewed-no-change`, or `no-impact`,
with a concrete reason. The service records the supplied review; it cannot prove
that a reviewer inspected the material.

```sh
ai-dlc project docs-disposition --base origin/main --decisions decisions.json --reviewer repository-maintainers
```

This emits content-bound evidence; explicitly save the reviewed output as
`.ai-dlc/documentation/current.json`. That reserved directory holds evidence only,
never source documents. Review the chosen comparison base as part of the evidence.
Do not reset it to hide changes. Changed document, source, mapping or change-scope
bytes invalidate the evidence and require another inspection.

An opted-in project can require `ai-dlc project docs-gate` through its normal check
manifest. First inspect historical diagnostics and explicitly review a baseline:

```sh
ai-dlc project docs-baseline --owner repository-maintainers --reason "Historical findings remain in the linked cleanup backlog."
```

Save only the accepted historical dispositions to
`.ai-dlc/documentation/baseline.json`. Baselines bind affected document bytes and
require an owner/reason. They are reviewable exceptions, not a command to suppress
all future errors. The gate rejects new objective errors, absent ownership and
uncatalogued documents. Unknown review dates and similarity require judgment.
Use `docs-gate --base <expected-base>` when CI supplies an independently selected
comparison. Existing repositories are not automatically enrolled.

## Evidence-backed semantic review

Prepare a small set of catalogued documents for the active harness:

```sh
ai-dlc project docs-review --base origin/main --path docs/reference/api.md --max-bytes 64000
```

The packet contains selected document bodies, mapped local evidence, hashes and
line numbers, plus omitted and unreviewed material. Budgets apply to body bytes;
large or unavailable files remain explicitly unreviewed. Links do not authorize
fetching remote content. Save the packet under the reserved evidence directory.

Review claims, not whole-document similarity scores. For each finding, cite an
exact target passage and supporting passages, identify uncertainty, and recommend
`revise`, `consolidate`, `retain`, or `investigate`. Categories distinguish
contradictions, unsupported claims, obsolete instructions, unnecessary repetition,
missing explanation, vague prose and useful repetition. A useful-repetition finding
uses `retain`. Preserve audience-specific summaries, warnings and unique rationale.
Two documents with similar words may answer different questions; two paraphrases
may still compete as the same authoritative instruction.

The review JSON identifies its packet snapshot, reviewed and unreviewed selected
paths, and findings. Each citation contains path, inclusive start/end line and the
exact quoted passage. Each finding supplies target, nonempty supporting citations,
uncertainty, suggested_disposition and rationale. The validator checks source bytes,
scope and citation grounding:

```sh
ai-dlc project docs-review-check --packet .ai-dlc/documentation/packet.json --review .ai-dlc/documentation/review.json
```

Passing establishes grounded citations, not semantic truth. Record partial coverage
honestly. Reconcile code/spec disagreements as defects or proposed requirement
changes; never silently rewrite approved intent to match an implementation bug.
Consolidation remains a reviewed Git edit: choose the canonical explanation, retain
unique facts and historical rationale, and link from supporting documents.

## Linked personal workspace

```sh
ai-dlc project workspace-init --vault /path/to/vault --name example --bases
ai-dlc project workspace-init --vault /path/to/vault --name example --bases --apply
```

The first call previews exact additions. The existing project portal remains
unchanged. A companion `Projects/example-workspace.md` organizes private focus,
daily links, questions and learnings. This has a distinct personal purpose; it does
not copy canonical documents. Existing annotations survive repeated setup.
Templates in `AI-DLC/Templates/` provide small structured notes; set their `project`
property to the workspace link and distinguish evidence from interpretation.
Optional native Bases views in `AI-DLC/Views/` show active projects, unresolved
questions and unreviewed learnings. Open those views in Obsidian; normal backlinks
and links also work without Bases. No community plugin is required by this setup.

At day start, select the relevant project and unresolved questions, then consult
current tracker/spec/code evidence. At day end, capture selected learning or an
unresolved question with its source links; do not copy every tool log or summarize
all activity automatically. Promotion to a team rule is a separate reviewed action.

## Company knowledge and SDK practices

Keep existing company policies and Confluence pages authoritative. A private
learning is an observation until evidence and a responsible owner establish its
applicability. Promote a selected observation into a candidate procedure, review it
against SDK behavior and company rules, then distribute the approved skill through
a pinned private Git bundle. Procedure and reference material have different jobs:
the skill states when/how to act; supporting references contain examples, rationale,
source provenance and limitations. Load only material needed for the current task.

Select separate bundles for unrelated company contexts. Record exact supported
SDK versions and the project's selected versions; incompatibility or unknown
applicability must be resolved before claiming readiness. Do not pretend all SDKs
share one semantic-version convention. Preserve authored local edits when upgrading
pinned guidance. Never automatically promote personal notes, fetch all Confluence
pages, or choose a winner when company guidance conflicts with project policy.

## Formatting and prose checks

The existing Markdown link/metadata checks remain objective diagnostics. Optionally
configure Vale and run `ai-dlc project docs-style --path docs/reference/api.md`.
AI-DLC invokes only the explicit check, never installs styles or runs Vale sync.
The default reports unavailable tools and alerts without a mandatory failure;
`--strict` requires the configured style check to pass. Keep local vocabulary and
style policy reviewed. A prose linter cannot verify implementation claims.

A schema-2 bundle keeps the original manifest fields and adds `references` and
`guidance`. For exported skill `sdk-requests` at `skills/sdk-requests/SKILL.md`,
its `references` entry can list `skills/sdk-requests/references/requests.md`.
Include every referenced file in the manifest `files` digest map. The supporting
path retains that relative location beside each rendered native skill.

Its `guidance` entry contains an owner, `status` (`approved`, `draft`, or
`superseded`), nonempty HTTPS `sources`, and `sdk` with `name` plus exact supported
`versions`. Declare the project's chosen version under `[agents.sdk_versions]`,
for example `example-sdk = "2.0"`. Draft/unknown/incompatible guidance may be
previewed and imported for inspection but cannot claim ready or render as active
guidance. Schema-1 bundles continue to work unchanged.

CI can set `AI_DLC_DOCS_BASE` to its independently selected PR base or push
predecessor; the `docs-gate` CLI uses it unless `--base` is explicitly provided.
Fetch that commit/history before checking. A stale or unavailable comparison must
be reviewed or fetched, not silently replaced with HEAD to hide changes.
