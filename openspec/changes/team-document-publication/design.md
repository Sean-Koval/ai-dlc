## Product decision under review

The maintainer prefers local drafts with selective publication. Propose repository
Markdown as the editable source for explicitly enrolled team documents; Confluence
holds published pages and remains authoritative for existing team-owned sources. Teammate page edits produce a conflict requiring
reconciliation. If the maintainer needs Confluence-first authoring or two-way
synchronization, revise this spec before implementation. Native read/search/link
access can be configured independently through the existing custom MCP server.

## Decisions

Activate publication for the optional `roles.documents = "<provider-alias>"`
selection introduced by this deferred document-integration change after the
custom server is reviewed; keep
`roles.knowledge = "obsidian"`. The new documents role has no default and does not
enter WorkService finish, existing Work binding defaults, or the note append API.
Publication has its own source/target binding records. Extend contract discovery
deliberately; this change owns scaffold/component role admission and optional
native document connections. Tracker onboarding #19 supplies reusable primitives
only and is not blocked by this deferred role.

Define typed operations `document_read` and `document_publish`. Read consumes an
explicit target reference and returns provider/account/space/page identity,
version and body digest. Publish consumes a stable operation ID, explicit create
or update intent, target identity, converted body, source digest, and an expected
remote version for updates. A new optional publication CLI and MCP facade call
the same service; the harness cannot substitute an unreviewed body for a saved plan.

Use `PublicationPlan` schema 1 under ignored `.ai-dlc/local/`: exact selected source
path and digest, provider/account/site/space/parent/page identity, create/update
intent, expected remote version/body digest, converted payload/digest, operation
ID and reviewable conversion warnings. Apply re-reads source and remote state;
no force-overwrite option in the first delivery. Existing pages can be adopted
only by explicit reference and review; title equality is not ownership.

Create previews include an explicit reviewed title and parent/space. An update
preserves the existing title unless a title change is separately present in the
reviewed payload. Confluence updates submit the next expected version so the
server rejects a concurrent change after preflight as well as before it.

First review the existing custom Confluence MCP server (document graph, semantic
descriptions, quality grading, writing/pushing via Claude and Antigravity). Prefer
its existing operations or a narrow bridge if they satisfy the typed contract.
Confluence Cloud REST v2 remains a candidate fallback only for an identified gap;
do not duplicate the graph or grading system. Record whether safety resides in
the existing server, an improvement there, or the AI-DLC adapter before coding. Implement a tested Markdown subset: headings, paragraphs,
lists, emphasis, links, fenced code and simple tables. Reject unsupported raw HTML,
Obsidian-only links/embeds, macros and attachments before apply; do not silently
drop them. Relative document links require an explicit known target page mapping
or a stable reviewed repository link. Select and pin a maintained conversion
dependency only after checking fidelity; do not build a general document editor.

Store non-secret durable source/target/version/digest/operation receipts in
`.ai-dlc/publications/`. Credentials remain local. Unknown remote mutation outcomes
remain journaled and block blind recreation. For new pages, the adapter must prove
a durable correlation/reconciliation strategy in a disposable space; if the API
cannot establish absence after uncertainty, require explicit target recovery.

Only explicit source files beneath approved repository document roots are eligible.
The initial default eligible root is `docs/`; additional repository roots require
an explicit reviewed publication setting. Reject symlink escapes and configured
private/daily-note roots. Never discover publication sources by scanning a vault.
Repository documents explicitly selected under eligible roots remain eligible
when viewed or edited in Obsidian, including when a repository is opened as a
vault; the viewer does not change their ownership. External vault files are not
implicitly eligible. Viewing local Markdown does not enroll notes for publication.
Private material may inform a separately reviewed shared draft, but publication
does not traverse that draft's private source links or attach linked vault files.
Confluence reads and requested local summaries use this change's DP-07 selective
guidance, transferred from former PT-05. Inventory the actual custom server before
rendering that guidance or qualifying native tools. This change adds no
synchronization engine.
Readiness only
checks this optional capability when selected/requested. Existing note CLI/MCP
helpers continue to use the configured vault and are not rewritten for Confluence.
