# Diagnose and qualify document organization and Obsidian workspace setup

## Context
The user approved the four-deliverable program and native local editable mounts. Existing document review requires catalog enrollment, docs-init is additive navigation only, and link-vault defaults to file-link portals.

## Goals / Non-Goals
Implement the requirements below using existing shared services. No autonomous relocation engine, vault mirror, Jira integration or changes to inaccessible company files.

## Decisions
- Keep service implementations in src/ai_dlc/documentation and CLI/MCP as adapters.
- Harnesses supply semantic judgment and ordinary Git edits; tooling reports scope, evidence and conflicts.
- Preserve existing portal and private-note defaults. Mount bindings stay local; stable checkouts own canonical bodies.
- docs/ contains appropriate architecture, ADR/decisions, runbook, reference and archive folders; openspec/ retains formal ownership.
- Review affected canonical guides and record content-bound documentation dispositions.

## Risks / Trade-offs
Symlinks require real client qualification; tests prove only exercised filesystem behavior. Missing client or company evidence is explicitly pending. Scoped review cannot certify all documentation.

## Migration Plan
Opt in to new commands and mount mode; preserve old configuration and authored content. Review exact Git diffs and use existing verification and finish gates.
