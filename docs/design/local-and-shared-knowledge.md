# Local and shared knowledge relationship

Status: proposed workflow, September 7, 2026, based on maintainer clarification.
Parent: [provider toolsets PRD](provider-toolsets-prd.md).

## Ownership and movement

| Material | Home | How it is used elsewhere |
| --- | --- | --- |
| Journal, scratch notes, daily work log and personal learnings | Local Obsidian vault | Selected local context for personal assistant agents; no automatic publication |
| Existing product knowledge, team guides and shared documents | Confluence Cloud | Relevant page links and on-demand reads; optional deliberate local summaries |
| A new document intended for teammates | Explicit local shared-draft location, initially repository `docs/` | Reviewed publication to a selected Confluence destination |

Confluence is authoritative for existing team pages. A local summary is a dated
derivative, not a synchronized replacement. For an explicitly enrolled local
publication source, retain its page binding and expected version; a teammate edit
requires reconciliation instead of overwriting or silently choosing a winner.

An example workflow: link a relevant team guide in a daily note, ask an agent to
read it for the current task, and optionally save a short summary with source URL,
version when available and retrieval date. Keep personal observations separate.
Later, select useful learnings to draft a team guide in an eligible shared-doc
location. Review the entire outgoing document and destination before publishing.
Private note inclusion is never inferred from a link, tag or neighboring file.

## Existing integration

The maintainer uses a custom Confluence MCP server exposing a graph of documents,
page descriptions and LLM-derived semantic information, and quality grading for
documents, spaces and pages. Claude and Antigravity help write and push documents.
These are user-reported capabilities; code, tool schemas, auth and live behavior
have not been inspected. The repository path or documentation is the next input.

Use the existing graph and quality functions instead of rebuilding them in AI-DLC.
Check whether graph queries can return a relevant subset without exporting the
whole graph into local notes. Treat LLM descriptions and quality grades as derived
aids with source links, not authoritative page content. Reuse existing writes
where their preview, conflict and recovery behavior meets the chosen guarantee.
If an existing tool cannot supply those guarantees, expose that limitation and
choose between improving the custom server or a narrow AI-DLC bridge after review.
Do not automatically install a second Atlassian connection for Confluence.

## Smallest useful integration

1. Inventory existing Confluence tools: client/connector/scripts, authentication,
   search/read support, output formats, page links/version metadata, conversion,
   preview/update behavior and how teammate edits are handled. Ask for names and
   workflow descriptions first, not credentials or bulk workspace content.
2. Attach the appropriate existing connection and generate project guidance for
   the current task's relevant spaces/pages. A relevance scope is not an access
   control mechanism; the upstream account still determines actual permissions.
3. Start with page links and reads on request. Let the user explicitly save a
   summary or extract to their selected local location, subject to work policy.
   Refresh selected derived content explicitly, keeping personal annotations and
   identifying stale, unavailable or inaccessible sources honestly.
4. Reuse existing publication tools if they meet the chosen workflow. Implement
   the optional publication service only for a demonstrated unmet guarantee.

Do not create another connector, automatic site crawler, shared search index,
vault mirror or two-way sync engine. Private local context stays out of outgoing
page payloads unless the user explicitly selects and reviews a derived shared
draft. This is a workflow and publication-source boundary, not a promise that
model processing is on-device or that native tools enforce AI-DLC guidance.

## Qualification examples

- Reading one selected page does not create any vault files or bulk read its space.
- Saving a requested summary records provenance and keeps personal annotations
  distinct. Refresh does not erase them or misrepresent inaccessible content as fresh.
- Drafting from private notes produces a separate candidate shared document; only
  its reviewed body is published, without linked daily notes or vault attachments.
- Editing a team page after a publication preview produces a conflict in any
  workflow claiming AI-DLC's deterministic publication guarantee.

Generated-guidance fixtures verify that these instructions are present and scoped.
Actual behavior of the selected tools requires separate live qualification.
The custom server repository/interface is still pending; no existing integration
was inspected or replaced.

## Project navigation

The [project documentation model](project-documentation.md) defines canonical navigation, optional catalog diagnostics and local Obsidian portals. It preserves OpenSpec ownership and does not introduce Confluence publication or synchronization.
