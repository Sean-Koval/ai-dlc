# Provider toolset planning handoff

## Latest adoption update — September 7

[Draft PR #23](https://github.com/Sean-Koval/ai-dlc/pull/23) contains the GitHub
workflow implementation and Project default (`19995aa`). Platform CI is pending.
No merge, archive or work finish has occurred.

Latest direction: ignore Linear reconciliation for now and work from the GitHub
issues. Project-backed GitHub setup is now the requested default. The bounded
`github-project-defaults` child of issue #19 has a formal specification, tests
and implementation accepted by independent review. Review found retry identity
and late repository drift gaps; regression tests now cover the fixes, including
host capitalization. All five required checks passed with 1,137 tests and all
15 strict OpenSpec items passed against the final implementation tree. This is
pre-commit local candidate evidence; see the verification record. Do not close
the parent for this slice alone.


The maintainer authorized practical adoption using current specs if the connected
Linear source is unavailable. Thirteen AI-DLC issues are now published and verified
in `Sean-Koval/ai-dlc` and attached to the
[AI-DLC Project #2](https://github.com/users/Sean-Koval/projects/2), with All work
and Delivery board views. See the [migration record](../planning/github-backlog-migration.md).
Repository selection is resolved. Jira is work onboarding only, with no Jira
migration. Repository-to-Project linking and local binding/default migration
remain pending the CLI Project permission upgrade; MCP Project access is verified. The older execution and
planning notes below are historical wherever this update supersedes them.


Execution update: user authorized implementation and selected GitHub Issues plus
Projects. The local implementation/review cycle on `codex/github-ticket-workflows`
is complete: capabilities, optional Project statuses, named setup and verified
selected/default migration. All five required checks passed with 1,123 tests;
all 14 strict OpenSpec items passed. Independent review fixes for GitHub account
and Linear team identity were accepted. See the
[qualification and activation requirements](../verification/github-ticket-workflows.md)
and [setup guide](../github-ticket-setup.md). Live activation, source backlog
inventory and exact target/creation review remain pending. The branch starts
from planning commit `0775b90`, under `.ai-dlc/work/github-ticket-workflows.toml` and the corresponding
child OpenSpec change. GitHub Projects is now in scope; prior exclusion and
undecided-destination notes are superseded. Plane is optional, Confluence deferred.

Objective: preserve AI-DLC's role as scaffolding and harness setup while making
supported tools easy to select and replace. The maintainer requested a code/state
review, implementation planning, formal specs for needed improvements, and a
clear account of required user inputs.

Branch: `codex/provider-toolset-plan`, based on main `9b6ca29`.
Local work: `.ai-dlc/work/provider-toolset-plan.toml`, unreviewed planning record;
no tracker issue was published and no remote priority/status was changed.
The independent SAN-12 branch remains at `04c65cb` with its separate cleanup
blocker; its implementation is not included or assumed merged here.

## Current priority

Latest maintainer steering: focus on task/ticket management using GitHub Issues
and Projects for personal coding projects; retain Linear as the source for
active/planned migration. Jira Cloud remains the work target. Defer Confluence
and publication; the custom server is on the work laptop and will be shared later.
Do not request that server as a prerequisite or deploy Plane to settle the choice.
Guided GitHub setup is implemented; live shared qualification remains pending.
GitHub Projects is included in the authorized `github-ticket-workflows` child.

## Review entry points

1. [PRD and user-input table](../design/provider-toolsets-prd.md).
2. [Code audit and alternatives](../planning/provider-toolset-code-audit.md).
3. [Dependency-ordered plan](../superpowers/plans/2026-09-06-provider-toolsets.md).
4. Four draft OpenSpec changes: `provider-toolset-onboarding`,
   `portable-tracker-adapters`, `selective-tracker-migration`, and
   `team-document-publication`. Each has a detailed linked child plan.

## Proposed direction

Reuse upstream MCP tools for Plane/Jira and the existing custom Confluence MCP
server for shared knowledge and document operations, subject to interface review.
Add only the narrow lifecycle adapters needed by AI-DLC's own work commands.
Improve explicit scaffold choices, generic connection setup, capability reporting
and native guidance. Separate default selection from selected-record migration.
Keep Obsidian knowledge local. Confluence native access does not require the
optional deterministic publication service.

## September 7 clarification and remaining inputs

- Plane is not installed; host it on the local computer, with a separate machine
  deployment runbook. Work targets Jira Cloud and Confluence Cloud.
- Earlier Linear-to-Plane confirmation is superseded by the latest destination
  choice: GitHub Issues and Projects. Plane remains optional for later adoption.
  Review inventory and mappings before execution.
- Obsidian holds private journals, daily logs, scratch notes and a personal
  knowledge base. Confluence holds shared product/team knowledge. Prefer local
  drafting and explicit publication of selected shared documents.
- Use [selective knowledge access](../design/local-and-shared-knowledge.md): links
  and reads on request, deliberate local summaries with provenance, no site/vault
  mirror. Existing team pages remain Confluence-owned.
- Existing Confluence tooling is a custom MCP server with a document graph,
  semantic descriptions and quality grading, used with Claude/Antigravity to
  write and push documents. Its repository path/URL or interface docs are pending;
  review it before selecting or building publishing machinery. Permitted
  authentication/client access and local deployment details remain to be established.

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

September 7 revisions update planning and specifications only. All four strict
spec validations, local links in 14 changed documents and whitespace checks passed
for this revision. The 963-test run above is prior baseline evidence, not a new
runtime or live-service claim; the full suite was not repeated for prose edits.

The subsequent ticket-priority revision passed 28 existing provider/rebind tests,
strict validation of all four draft changes, local-link checks in 14 changed
documents, TOML syntax and whitespace checks. These checks do not qualify the
proposed GitHub/Plane migration paths or new onboarding; those remain specified
future work. No full-suite rerun or live provider calls were made for this revision.

No runtime code, active provider selection, account settings, tracker bindings,
remote issues, or shared pages were changed. No archive, PR, merge, or work finish
was attempted. User input may revise these drafts; resolve scope before marking
child implementation work reviewed, publishing its tracker items, or executing it.
