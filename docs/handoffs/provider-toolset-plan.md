# Provider toolset planning handoff

Objective: preserve AI-DLC's role as scaffolding and harness setup while making
supported tools easy to select and replace. The maintainer requested a code/state
review, implementation planning, formal specs for needed improvements, and a
clear account of required user inputs.

Branch: `codex/provider-toolset-plan`, based on main `9b6ca29`.
Local work: `.ai-dlc/work/provider-toolset-plan.toml`, unreviewed planning record;
no tracker issue was published and no remote priority/status was changed.
The independent SAN-12 branch remains at `04c65cb` with its separate cleanup
blocker; its implementation is not included or assumed merged here.

## Review entry points

1. [PRD and user-input table](../design/provider-toolsets-prd.md).
2. [Code audit and alternatives](../planning/provider-toolset-code-audit.md).
3. [Dependency-ordered plan](../superpowers/plans/2026-09-06-provider-toolsets.md).
4. Four draft OpenSpec changes: `provider-toolset-onboarding`,
   `portable-tracker-adapters`, `selective-tracker-migration`, and
   `team-document-publication`. Each has a detailed linked child plan.

## Proposed direction

Reuse official upstream MCP tools for general Plane/Jira/Confluence interactions.
Add only the narrow lifecycle adapters needed by AI-DLC's own work commands.
Improve explicit scaffold choices, generic connection setup, capability reporting
and native guidance. Separate default selection from selected-record migration.
Keep Obsidian knowledge local. Confluence native access does not require the
optional deterministic publication service.

## Decisions still needed

- Plane hosting state and URL if available; if absent, choose hosting separately.
- Jira/Confluence Cloud or Data Center and permitted authentication/client access.
- Default-only switch versus migration of selected existing Linear work.
- Document authoring direction and whether native page tools suffice or AI-DLC
  should own repeatable publication. Repository-first publication is only the
  proposed optional scope; two-way synchronization is not designed here.

Project/space URLs or friendly names, local sign-ins and vault attachment are
needed for connection later. Discovery should resolve IDs and available states;
the user should not retrieve raw UUIDs or provide secrets in chat.

## Validation and boundaries

Source bootstrap completed. The source-audit focused suite passed 148 tests.
Required project checks passed all five outcomes with 963 full tests. Strict
OpenSpec validation passed for all four draft changes; local links and work
record parsing were verified. These are local baseline/artifact checks, not
new provider implementation, independent design acceptance, live qualification,
or merged-revision CI evidence.

No runtime code, active provider selection, account settings, tracker bindings,
remote issues, or shared pages were changed. No archive, PR, merge, or work finish
was attempted. User input may revise these drafts; resolve scope before marking
child implementation work reviewed, publishing its tracker items, or executing it.
