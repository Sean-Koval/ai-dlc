## Why

Deferred: maintainer requests ticket-management focus. The custom server will be
shared later; this draft remains open for revision and is not an implementation
dependency for GitHub Issues, Plane or Jira.

Private notes and team publication are distinct responsibilities. The existing
knowledge append contract cannot represent controlled updates to shared documents.
Status: proposed; local drafting with selective publication is preferred. Review
the existing custom Confluence MCP server before choosing implementation scope.
[Requirements](../../../docs/design/provider-toolsets-prd.md).

This is an optional stronger publication guarantee. Native Confluence tools and
guidance can satisfy ordinary team document access/editing without this service;
do not implement this change merely to connect Confluence.

## What Changes

- Add an optional documents role and explicit publication service alongside Obsidian knowledge.
- Preview selected repository Markdown against Confluence targets and remote versions.
- Apply only reviewed content; preserve teammate edits through conflict refusal.
- Store publication provenance and recover uncertain operations without duplicate pages.

## Capabilities

### New Capabilities
- `team-document-publication`: explicit version-aware shared document publication.

### Modified Capabilities
None. Private note operations and work finish retain their existing behavior.

## Impact

Contracts/registry, optional role metadata/scaffold choices, new publication service,
a qualified bridge to the existing custom Confluence MCP server or a Cloud adapter
for demonstrated gaps, CLI/shared MCP facade, publication records and tests.
No automatic publication at finish, vault mirroring, two-way sync, or Data Center
claim. [Plan](2026-09-06-team-document-publication.md).
