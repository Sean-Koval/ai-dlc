# Template Extension Workflow (Direct Commands)

## Purpose
This guide mirrors the multi-agent template extension flow but relies solely on commands outside `sc_commands/`. It shows how to coordinate agents and deliver updates to `.claude/commands/` or `.claude/agents/` using the standard command folders (e.g., `todo`, `project-management`, `documentation`).

## Core Agents
- **workflow-orchestrator** – coordinates milestones and agent handoffs (`templates/claude/.claude/agents/09-meta-orchestration/workflow-orchestrator.md`).
- **research-analyst** – investigates demand, prior art, and user needs (`templates/claude/.claude/agents/10-research-analysis/research-analyst.md`).
- **fullstack-developer** – implements prompt and embedded template updates (`templates/claude/.claude/agents/01-core-development/fullstack-developer.md`).
- **documentation-engineer** – maintains docs and help surfaces (`templates/claude/.claude/agents/06-developer-experience/documentation-engineer.md`).
- **code-reviewer** – performs structured review and validation (`templates/claude/.claude/agents/04-quality-security/code-reviewer.md`).

## Command Palette (non-`sc_commands`)
| Goal | Command |
| --- | --- |
| Prime repository understanding | `/context-prime:context-prime` |
| Build reference dossiers | `/initref:initref` |
| Track work items | `/todo:todo ...` |
| Generate product requirement prompt | `/project-management:create-prp "Feature" --research` |
| Draft PRD | `/project-management:create-prd "Feature"` |
| Create feature scaffolding & plan | `/project-management:create-feature "Feature"` |
| Update documentation | `/update-docs:update-docs` |
| Capture changelog entries | `/add-to-changelog:add-to-changelog "message"` |
| Prepare commits | `/commit:commit` |
| Generate pull request | `/create-pr:create-pr` |
| Trigger PR review | `/pr-review:pr-review` |
| Build release note | `/release:release` |
| Manage testing plan | `/testing_plan_integration:testing_plan_integration "<area>"` |

Use these commands alongside direct instructions to agents (`@workflow-orchestrator`, `@fullstack-developer`, etc.).

## Phase 0 – Kickoff
```bash
/context-prime:context-prime
/initref:initref
/todo:todo add "Deliver template-spec command" next week
@workflow-orchestrator "Coordinate template-spec command initiative"
/project-management:create-feature "template-spec command"
```
1. Prime Claude with repo context and create reference docs.
2. Register the new initiative in `todos.md`.
3. Ask the orchestrator to review the generated feature plan and highlight dependencies.

## Phase 1 – Product Framing
```bash
@research-analyst "Collect user stories motivating template-spec command"
/project-management:create-prp "template-spec command" --research
/project-management:create-prd "template-spec command"
```
- Produce a Product Requirement Prompt and PRD to capture scenarios, target personas, and quality bars.
- Share artifacts with the orchestrator and developer to align on scope.

## Phase 2 – Technical Blueprint
```bash
@workflow-orchestrator "Translate PRD into implementation checklist"
/todo:todo add "Sync embedded templates" tomorrow
/todo:todo add "Update README usage" tomorrow
/documentation:docs-maintenance --audit "template-spec documentation gaps"
```
- Break PRD into tactical todo items.
- Use documentation maintenance command to audit current docs for necessary updates.

## Phase 3 – Implementation
```bash
@fullstack-developer "Implement template-spec command prompts and embedded assets"
/act:act
/commit:commit
/commit:commit
```
- Use `/act:act` to follow the RED–GREEN–REFACTOR cycle.
- After changes, stage focused commits via `/commit:commit`.

## Phase 4 – Verification
```bash
@code-reviewer "Validate template-spec command output and regression risk"
/testing_plan_integration:testing_plan_integration "template-spec"
/todo:todo add "Capture validation log" today
```
- Invoke the testing plan command to outline verifications (scaffold run, hidden directory check, etc.).
- Track any findings as todos for follow-up.

## Phase 5 – Documentation & Communication
```bash
@documentation-engineer "Refresh docs for template-spec command"
/update-docs:update-docs
/add-to-changelog:add-to-changelog "feat(claude): add template-spec command"
```
- Update README and workflow docs.
- Append a changelog entry to surface the new capability.

## Phase 6 – Integration & Release
```bash
/create-pr:create-pr
/pr-review:pr-review
/release:release
```
- Produce a PR with context links to the PRD, commits, and testing evidence.
- Route through `pr-review` for structured QA.
- Draft release notes for when the change ships.

## Phase 7 – Closeout
```bash
@workflow-orchestrator "Confirm closure and archive supporting docs"
/todo:todo complete 1
/add-to-changelog:add-to-changelog "chore: archive template-spec research"
```
- Confirm all todos resolved.
- Archive temporary research or note follow-up actions.

## Output Checklist
- Updated `.claude/commands/` or `.claude/agents/` assets.
- Embedded templates synced (`scripts/sync-cli-templates.sh`) and rebuilt.
- PRD/PRP and testing plan stored for traceability.
- Documentation and changelog entries reflecting the new command.
- Release notes drafted for rollout.

By relying solely on commands outside `sc_commands/`, this workflow fits teams who prefer the classic AI-DLC command palette while still coordinating multiple agents.
