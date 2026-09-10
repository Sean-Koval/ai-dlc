> Historical record. Retained for provenance, not current implementation guidance.
> Consult docs/index.md, canonical OpenSpec requirements and the tracker.

# Team Document Publication Implementation Plan

Current scope (September 7): deferred under #22 pending the actual custom server.
This change owns documents-role/scaffold/component/native admission and DP-07
selective knowledge guidance formerly assigned to #19. Reuse common connection
primitives when available; do not make current tracker/native-client onboarding
depend on this deferred integration.

Deferred by September 7 maintainer direction. The custom server is on the work
laptop and will be shared later. Keep this draft for future interface review;
none of its tasks or access requirements block ticket-management delivery.

> **For agentic workers:** Use superpowers:executing-plans only after existing-tool reuse and the remaining publication gap are reviewed.

**Goal:** Publish reviewed repository documents to Confluence while retaining private Obsidian notes.
**Architecture:** Optional documents role, separate publication service and records, version-aware Confluence adapter; native tools provide general reading/editing.
**Tech Stack:** Existing Python/httpx/Pydantic/MCP; reviewed Markdown converter only if needed for the declared subset.
**Spec:** [team-document-publication](specs/team-document-publication/spec.md).

Status: draft for selected local-document publication to Confluence Cloud.
Local drafting is preferred; review the existing custom MCP server before choosing
the backend or treating the proposed new provider files below as necessary.
[Master constraints](../../../docs/archive/planning/2026-09-06-provider-toolsets.md) apply. If the maintainer selects
Confluence-first or two-way authoring, revise scope before starting these tasks.

## Task 0: Reuse assessment before implementation

- [ ] Inspect the custom MCP server repository/tool schemas, connection and account
  binding, scoped graph/read operations, page/version provenance, write payloads,
  quality checks and behavior after conflicts or lost responses.
- [ ] Rehearse one local shared draft through the existing Claude/Antigravity flow
  in a designated test destination only after live access is authorized.
- [ ] Map existing behavior to DP requirements. If the existing workflow suffices,
  deliver setup/guidance and leave this optional service unstarted. Otherwise
  choose an improvement in that server or the smallest bridge/adapter needed.
- [ ] Revise the proposed files/interfaces below to reflect that evidence; do not
  build another document graph, semantic index or quality-grading service.

## Task 1: Optional publication contract and source boundary

**Files:** `contracts.py`, `providers/__init__.py`, provider definitions and
generated `contracts/`; create `publication.py`, `tests/test_publication.py`;
extend configuration/component tests. Consume the optional documents selection
already admitted by the toolset-onboarding change; do not introduce it twice.
**Interfaces:** `preview_publication(root: Path, provider_id: str, source: str, target: dict, *, environ) -> dict`; `apply_publication(root: Path, plan: dict, *, environ) -> dict`.
New document_read/document_publish payloads follow the design's identity, version,
body/digest and operation fields; use strict Pydantic models and generated schemas.

- [ ] Add a red pure-file test rejecting a selected document that symlinks into the vault, before any provider invocation:

```python
def test_publication_does_not_follow_vault_link(publication_project):
    root, vault = publication_project
    (root / "docs/private.md").symlink_to(vault / "daily.md")
    with pytest.raises(ValueError):
        preview_publication(root, "confluence-work", "docs/private.md",
                            {"space": "team-space"}, environ={})
```

- [ ] Verify red, implement explicit eligible roots/source validation, optional documents selection, and separate publication bindings. Add no default documents role or finish side effect.
- [ ] Test unselected provider behavior, source edits after preview, alias/account drift, strict plan tampering refusal, and unchanged note operations; commit after focused checks.

## Task 2: Confluence versioned publication and conversion

**Files:** create `providers/confluence.py`, `document_conversion.py`,
`tests/test_confluence_provider.py`, `tests/test_document_conversion.py`;
extend publication service and provider definition metadata.
**Interface:** `ConfluenceProvider(config, *, client=None, environ=None)` supports
document_read/document_publish. `convert_document(content: str, links: dict[str, str]) -> dict`
returns converted body, digest and source-location diagnostics; unsupported constructs block apply.

- [ ] Test literal conversions for the declared Markdown subset, unsafe links, unresolved relative targets and unsupported Obsidian embeds.
- [ ] Test a teammate edit between preview and apply; assert zero write requests and exact remote content retained. Test page-ID/space mismatches and title collisions independently.
- [ ] Verify red, implement API version preconditions and explicit create/adopt/update intent. Select a maintained converter only after subset fidelity tests; record/pin the dependency if added.
- [ ] Add uncertainty tests for create accepted with lost response and update applied before local receipt failure. Require deterministic reconciliation or explicit recovery; never blind retry create.
- [ ] Implement durable publication receipts and retry journals; verify no private-note content in requests. Run focused tests and commit.

## Task 3: Shared CLI/MCP interface and live publication proof

**Files:** `cli.py`, `mcp_server.py`, provider guidance, `readiness.py`, new
`tests/test_publication_cli.py`, `tests/test_publication_mcp.py`, verification runbook.
**Interface:** both facades consume the same saved publication plan and shared service.

- [ ] Test that both interfaces refuse unreviewed/stale plans and return the same source/page/version evidence.
- [ ] Connect the actual permitted Confluence site/space; show a converted preview of one nonprivate fixture document.
- [ ] In the disposable target, prove create/update, version conflict, duplicate-safe recovery and no automatic publication on work finish.
- [ ] Inspect final page rendering in the actual service; HTTP success alone does not establish document fidelity.
- [ ] Run required checks and strict spec validation; complete independent review and record actual supported environments before archive/finish.

Coverage: Task 1 DP-01/DP-02/DP-06; Task 2 DP-02/DP-03/DP-04/DP-05; Task 3 interface parity and live evidence.
