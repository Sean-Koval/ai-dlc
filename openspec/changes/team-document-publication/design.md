## Product decision under review

Propose repository Markdown as the editable source for selected team documents;
Confluence holds published pages. Teammate page edits produce a conflict requiring
reconciliation. If the maintainer needs Confluence-first authoring or two-way
synchronization, revise this spec before implementation. Native read/search/link
access can be configured independently through upstream tools.

## Decisions

Activate publication for the optional `roles.documents = "<provider-alias>"`
selection introduced by provider-toolset-onboarding; keep
`roles.knowledge = "obsidian"`. The new documents role has no default and does not
enter WorkService finish, existing Work binding defaults, or the note append API.
Publication has its own source/target binding records. Extend contract discovery
deliberately; the preceding setup change owns scaffold/component role admission.

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

Confluence Cloud REST v2 is the first backend, with native MCP remaining available
for general interaction. Implement a tested Markdown subset: headings, paragraphs,
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
Readiness only
checks this optional capability when selected/requested. Existing note CLI/MCP
helpers continue to use the configured vault and are not rewritten for Confluence.
