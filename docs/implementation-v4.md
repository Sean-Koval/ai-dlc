# AI-DLC v4 implementation ledger and acceptance map

Authority: the user-approved AI-DLC v4 plan, September 2, 2026.

This is a historical implementation ledger. Its progress notes describe that
implementation period; use the [current roadmap](roadmap.md) and
[release evidence](release-verification.md) for present status. Preserve the
original v4 verification obligations when planning new capabilities.

## Global constraints

CLI and MCP share application services. Completion requires trusted CI evidence for
the merged revision. Setup delegates package/runtime/dotfile management. User content
must survive adoption and rendering. No credentials in tracked configuration. Normal
providers are trusted code; conformance testing must fail closed without isolation.
New provider bindings affect new work; recorded work stays bound until explicit rebind.
Targets are advertised as verified only after an actual walkthrough.

## Task 1: Foundation and project execution

Python packaging, scoped configuration with provenance, stable work schemas, setup/check
execution, receipts, standalone verified bootstrap, checked-out implementation in CI.

## Task 2: Providers and workflow services

Versioned contracts, discovery, integrity checks, Linear and executable GitHub Issues,
OpenSpec, GitHub evidence validation, journal/recovery, gated finish and separate handoff.
Provide service APIs consumed by CLI/MCP, with filesystem/HTTP boundary tests.

## Task 3: Portability, agents and adoption

Workstation modules; target capability manifests; deterministic managed agent sections;
Copier presets/adoption/updates; Obsidian operations; hooks with explicit coverage and
bounded reminders; cloud entry scripts; architecture/playbook/skills.

## Task 4: Integration and release verification

Wire all public commands/MCP; sandboxed conformance runner; profile capture/rebind;
release constraints/integrity; compatibility fixtures; docs and final review.

## Interface review

| Tasks | Shared boundary | Resolution |
|---|---|---|
| 1 / 2 | Work record and config | Plain JSON-compatible dictionaries at service boundary; Pydantic validation inside services. |
| 1 / 3 | Project config and assets | Project owns checks and bindings; machine owns local paths. |
| 2 / 4 | Work operations and MCP | CLI/MCP call identical WorkService methods, no raw provider completion tool. |
| 3 / 4 | Generated files and CI | Required generated check compares content without modifying tracked files. |
| 1 | Bootstrap versus self CI | Source mode runs uv sync --locked then checkout implementation. Release mode requires published wheel manifest. |
| 2 | Remote uncertainty | Correlation search before retry; fail on unresolved ambiguity. |
| 3 | Cloud and hook availability | Capability declarations and readiness failures, no simulated guarantees. |
| 4 | Sandbox availability | Docker/enforcement unavailable means test unavailable, never host fallback. |

## Progress

- Repository baseline: clean at 8c1bf1b; original Python CI references missing packaging.
- Implementation underway in isolated feat/portable-development-v4 worktree.
- Ruling: use official MCP SDK stable 1.x, pinned by uv.lock; v2 API migration is explicit.
- Release and live-target walkthroughs require built artifacts/available infrastructure;
  record evidence and remaining gaps instead of calling mock tests live verification.
