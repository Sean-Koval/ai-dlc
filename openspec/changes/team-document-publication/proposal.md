## Why

Issue #50 requests implementation using the production ai-docs source. On
September 14, 2026 the referenced source and md_to_confluence.py were absent from
the available local repository/work locations. The source inventory prerequisite
remains blocked; no alternative converter/client has been presented as its port.
No corporate remote service was accessed or qualified.

The independently specified local FDE scaffold and stage checks are delivered by
[fde-document-scaffold](../archive/2026-09-14-fde-document-scaffold/proposal.md). They do not complete
this change or issue #50. Remaining work includes inspecting the actual source,
porting/reusing conversion and transport under these safety contracts, selective
preview/apply, version conflicts, recovery/registry mapping, optional remote
hierarchy creation and disposable-space/harness qualification. Resolve the
issue's bidirectional-sync description against this proposal's deliberate
one-way reviewed publication contract when the source can be inspected.

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
