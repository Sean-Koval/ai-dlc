# Provider Toolsets Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for one reviewed child plan at a time. Delegate only when authorized. Checkboxes describe delivery, not planning approval.

**Goal:** Make ticket-provider selection routine and prove it with GitHub Issues,
Plane and Jira. Retain Obsidian; defer Confluence integration until its existing
custom MCP server is available for review.

**Architecture:** Reuse existing and upstream MCP tools for general service access and thin adapters for AI-DLC operations. Reuse current scaffolding, profiles, components, provider registry, owned harness rendering and evidence gates.

**Tech Stack:** Python 3.12, existing httpx/MCP/Pydantic/Typer/Copier stack, OpenSpec, native MCP integrations and Markdown guidance.

**Spec:** [Draft PRD](../../design/provider-toolsets-prd.md) and the four child OpenSpec changes below.

Status: proposed plan, updated September 7, 2026. No runtime changes or migration performed.
Approval of planning is not approval of account mutations, hosting, or live migration.

## Global Constraints

- Additive schema-4 behavior; preserve existing provider choices when new options are omitted.
- Keep provider request details out of WorkService; retain authored content and existing finish gates.
- Preserve old aliases and fingerprints; no automatic rebind or ticket closure.
- Keep secrets, OAuth state and vault paths local. Do not ask users for credential values in chat.
- Use existing native clients; no new daemon, marketplace, sync engine or hosting orchestrator.
- Test real file behavior and adapter requests. Fixtures do not establish live qualification.
- Bootstrap each implementation checkout and run its required manifest checks plus strict OpenSpec validation.
- Before modifying agents.py, reconcile the independently active SAN-12 branch and its remaining cleanup finding. Adapter-only work can proceed independently; do not assume SAN-12 has merged or waive authored-file safety for new apply paths.

## Delivery order

| Order | Deliverable | Plan | Dependency / release gate |
| --- | --- | --- | --- |
| 1 | Provider choices, reusable onboarding and native harness setup; prove with existing Linear behavior | [Toolset setup](2026-09-06-provider-toolset-onboarding.md) | Existing main foundations |
| 2 | Existing GitHub Issues onboarding and shared lifecycle qualification | [Tracker adapters, Tasks 1 and 1a](2026-09-06-portable-tracker-adapters.md) | Setup interfaces; no Plane deployment prerequisite |
| 3 | Plane native connection plus thin lifecycle adapter | [Tracker adapters, Task 2](2026-09-06-portable-tracker-adapters.md) | Setup interfaces; local deployment for live qualification |
| 4 | Rehearse default-only and selected migration for both destinations; switch personal work only after choosing a destination and reviewing mappings | [Migration](2026-09-06-selective-tracker-migration.md) | Qualified selected target; GitHub path does not wait for Plane |
| 5 | Jira adapter and work-project toolset; same lifecycle without another workflow branch | [Tracker adapters, Task 3](2026-09-06-portable-tracker-adapters.md) | Work deployment/authentication decision; can run alongside migration |
| Deferred | Optional deterministic Confluence publication with Obsidian retained | [Publication](2026-09-06-team-document-publication.md) | Review existing custom server when shared later; no dependency for ticket delivery |

Do not wait for all four changes to configure useful native access. Report that
access as such until the corresponding lifecycle adapter is delivered. Finish
each child through its own reviewed specifications, PR/CI evidence and work finish.
Split deferred document-specific setup requirements/tasks into a separate delivery
change before tracker implementation review; do not mark an entire mixed-scope
change complete with document requirements undelivered.
Do not close planning or implementation work merely because this plan validates.

The minimum Confluence integration is the existing custom MCP connection plus scoped
guidance. The publication service is a proposed optional extension, not required
for general team page editing. Leave that child unstarted if native tools meet
the maintainer's publishing needs.

## Definition of easy setup

For each supported toolset, a user supplies a service URL (or chooses an existing
connection), signs in, chooses named project/space/state options, and reviews a
single configuration preview. AI-DLC stores portable choices, identifies local
setup steps and renders client guidance. Opening another project chooses that
project's toolset; a second machine supplies only local authentication and paths.

Add a walkthrough to release evidence that records the number of required manual
steps and every raw-ID lookup. Acceptance requires zero manual ID lookup and zero
AI-DLC source edits for ordinary supported-provider selection. Do not promise a
fixed click count across different organization authentication policies.

## Decisions needed from the maintainer

Confirmed September 7: Plane is not installed and will be self-hosted on the local
computer; work uses Jira Cloud and Confluence Cloud. Migrate active/planned Linear work to the eventual selected personal tracker.
The latest decision reopens the destination between GitHub Issues and local Plane;
completed history is outside the initial migration scope.
Local drafting with selected publication is preferred. Obsidian remains a private
journal, scratch pad and personal knowledge base; Confluence remains the shared
library. Use the [selective knowledge relationship](../../design/local-and-shared-knowledge.md)
for guidance and qualification rather than site/vault synchronization.

Confluence work is deferred. Its code is on the work laptop and will be shared
later; that input is not needed for ticket planning or implementation.
Existing Confluence tooling is a custom MCP server with document graphs, semantic
descriptions and quality grading, used with Claude/Antigravity to write and push
pages. Still needed: its repository path/URL or tool documentation, to assess reuse
before implementing additional publication code. Attach this server first; do not
replace it with another connector by default. Site/project/space URLs, local
sign-ins and vault attachment are needed for connection and live verification
later. No credentials are needed in chat or for isolated adapter tests.

Prepare a separate local Plane deployment runbook using reviewed upstream
artifacts. Inspect the machine runtime, choose persistent storage and backups,
document start/stop/restore and keep initial exposure local. Report unavailable
service when the machine is off. Project bootstrap installs only required client
prerequisites; it does not recreate the server for each repository. Hosting
execution remains separate from this planning change.

## Review and verification

- [ ] Resolve scope-affecting user decisions and mark the affected child work reviewed.
- [ ] Run each child TDD plan and independent review before its release.
- [ ] Demonstrate native read/search access separately from each tracked-work lifecycle.
- [ ] Exercise personal/work isolation and second-machine continuation.
- [ ] Rehearse migration failures and Confluence version conflicts in disposable destinations.
- [ ] Record exact versions, environments, permissions, outputs and unverified targets.
- [ ] Update SAN-15 qualification scope through its owner; do not silently rewrite that active plan or treat older Linear/GitHub cases as Plane/Jira evidence.
