# ai-dlc product direction

Understand what ai-dlc promises to do, what it leaves to its neighbours, and
the user outcomes it is measured against.

Status: feature-frozen as of 2026-10 by
[ADR 0001](decisions/0001-refocus-ai-dlc.md), which owns the in-scope list.
Changes outside it are closed with a pointer; bug fixes in frozen areas are
welcome. The roadmap distinguishes implemented, proposed, cancelled and
unverified scope.

## Product promise

ai-dlc is a local workflow, machine-provisioning and work-lifecycle tool. It
prepares a developer machine and authors one optional workflow plugin of
guidance, hooks and team skills. It finishes reviewed work only against the
merged revision and its CI receipts. It does not evaluate harnesses (flightdeck
does) or define what runs in cloud sandboxes (hangar's claim-time renderer does).

Its durable value is the relationship between tools, artifacts, decisions, and
workflows. OpenSpec currently provides formal specification; personal projects
use GitHub Issues and Projects, while Jira Cloud is the selected work target.
The workflow plugin and managed sections target Claude Code and Codex; client
rendering is frozen (ADR 0001) and installed clients are unqualified. These choices
are replaceable.

The harness performs development and can use installed tools directly. ai-dlc
provides setup, guidance, integration, validation, and evidence services where
useful. Existing project policies still determine required checks and completion.

Teams should be able to scaffold their own development flow. They choose
supported tools and clients, keep repository policy and acceptance commands in
the project, and share only the guidance they need. Start with setup, selected
guidance and useful local checks; add tracked delivery, formal specifications
and other stages when the team's work needs them. Profiles and team sources
carry selected practices without making this repository's own process mandatory
downstream.

## Immediate adoption outcome

Install ai-dlc on the work computer and adopt work repositories with their own
Jira configuration and local credentials. Claude Code and Codex get the same guidance
from the plugin or managed sections. An engine clone must not enroll work projects
into ai-dlc's personal tracker. Keep Obsidian private; Confluence publication is cut.

## User outcomes

1. Enroll another supported machine/environment and recover the same selected
   tools and guidance with independent local credentials, paths, and accounts.
2. Open a new or existing repository and let the harness discover selected
   providers, installed tools, authoritative instructions, artifacts, and next action.
3. Shape a vague idea or observed problem into a worthwhile bounded increment,
   with evidence, assumptions, alternatives, and explicit success criteria.
4. Translate outcomes into behavioral specifications, deliverable tickets, and
   verification without repeatedly copying the same information.
5. Add or replace components with clear compatibility, ownership, and update rules.
6. Hand the workflow plugin to a team harness that can switch it on or off; flightdeck
   measures whether it helps.

## Responsibilities and replaceability

| Part | Stable responsibility | Implemented foundation | Qualification or proposed follow-on |
| --- | --- | --- | --- |
| Environment | Reproduce tools and local bindings | Bootstrap, enrollment, project setup and connected readiness | Qualify selected machine and installed clients |
| Integrations | Connect capabilities to selected systems | Provider metadata, contracts and scoped onboarding | Qualify actual selected provider deployments |
| Harness support | Author one optional workflow plugin; render managed sections into developer repos | The workflow plugin and its Codex form ([#191](https://github.com/Sean-Koval/ai-dlc/issues/191)–[#193](https://github.com/Sean-Koval/ai-dlc/issues/193), shipped); managed client guidance and pinned bundles | The team harness pins the plugin ([hangar#139](https://github.com/Sean-Koval/hangar/issues/139)); flightdeck compares runs with and without it |
| Workflows | Guide decisions and handoffs | Product shaping, traceability and optional Design PM guidance | Bug fixes only while frozen |

Evaluation of harnesses and guidance is not an ai-dlc responsibility: flightdeck
owns it. Required checks and finish gates still establish delivery evidence.

## Product development workflow

Greenfield starts with audience, problem, evidence, alternatives, and the smallest
useful outcome. Brownfield starts with observed behavior, users, integrations,
compatibility constraints, and an incremental change. Both converge on a shaped
outcome, requirements, applicable design, behavioral specification, delivery
slices, implementation, and verification. Findings can send work back to discovery.

Product requirements explain intent and scope. Specifications define observable
behavior. Tickets organize deliverable slices, dependencies, and status. Tasks
describe implementation steps. Links and stable IDs preserve these relationships.

UI/UX is one optional workflow in this sequence. Its generation/evaluation loop
serves changes requiring interaction or visual judgment. Other work uses suitable
methods: compatibility tests, architecture review, migration rehearsals, API
contracts, or operational evidence. Small work uses small artifacts.

## Principles and limits

- Keep recurring context small and relevant. Prefer short shared rules and links
  to task-specific guidance; measure cost and failures caught before adding more
  process. Required commands should test project behavior; product choices, test
  adequacy and design quality remain review judgments.
- Prefer existing tools; build integration where it removes coordination work.
  Tencent teamai repositories are a supported team-source format, not a runtime
  dependency; ai-dlc reads their safe, pinned subset through profile subscriptions.
  Prove a small component contract with real adapters before expanding it.
- Make installation, configuration, instructions, and readiness understandable
  together while preserving their separate data ownership.
- Carry portable state through versioned repositories; keep secrets and machine
  bindings local. Never infer an account from an unrelated session.
- Preserve authored content, active bindings, and existing contracts on updates.
- Make product choices explicit before coding; an executor must not invent scope,
  approval, evidence, or a missing cross-ticket interface.
- Measure observed outcomes. Green tests alone do not prove product value, user
  preference, or successful live platform qualification.
- Consistency means the same intended workflow with honest capability differences,
  not an assertion that every environment supports every tool.

## Delivery boundaries

Still to qualify: machine bootstrap on macOS and Linux, the workflow plugin in
Claude Code ([#53](https://github.com/Sean-Koval/ai-dlc/issues/53)), and the local
lifecycle against Jira Cloud ([#85](https://github.com/Sean-Koval/ai-dlc/issues/85)).
Each stays unverified until its walkthrough succeeds. Cloud execution is hangar's and
evaluation flightdeck's; the [scope freeze](decisions/0001-refocus-ai-dlc.md) governs
the rest.

The last release is v0.4.0 (September 14, 2026); the
[changelog](https://github.com/Sean-Koval/ai-dlc/blob/main/CHANGELOG.md) lists later
changes. Release-tracking issue #17 was cancelled as not planned.

## Navigation

- [ADR 0001: the scope freeze and in-scope list](decisions/0001-refocus-ai-dlc.md)
- [Roadmap](roadmap.md)
- [Current architecture](architecture.md)
- [Migration notes](migration.md)
- [Actual release evidence](release-verification.md)

Earlier plans are in git history and `openspec/changes/archive/`.
