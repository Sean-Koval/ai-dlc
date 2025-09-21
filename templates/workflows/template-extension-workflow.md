# Multi-Agent Template Extension Workflow

## Overview
Use this workflow to add or enhance assets under `.claude/commands/` or `.claude/agents/`. A root orchestrator coordinates specialized agents (research, development, documentation, review) while invoking the up-to-date slash command structure (`/<folder>:<command>`).

## Participant Agents
- **workflow-orchestrator** – end-to-end coordinator for task routing and state tracking (`templates/claude/.claude/agents/09-meta-orchestration/workflow-orchestrator.md`).
- **research-analyst** – gathers prior art, requirements, and risks (`templates/claude/.claude/agents/10-research-analysis/research-analyst.md`).
- **fullstack-developer** – implements prompt or command changes across the repo (`templates/claude/.claude/agents/01-core-development/fullstack-developer.md`).
- **documentation-engineer** – updates docs and help surfaces (`templates/claude/.claude/agents/06-developer-experience/documentation-engineer.md`).
- **code-reviewer** – verifies policy, quality, and regression coverage (`templates/claude/.claude/agents/04-quality-security/code-reviewer.md`).

## Core Slash Commands
| Purpose | Slash Command | Notes |
| --- | --- | --- |
| Prime repository context | `/context-prime:context-prime` | Reads README + repo inventory. |
| Build canonical references | `/initref:initref` | Generates `/ref` documentation. |
| Multi-agent orchestration | `/sc:spawn` | Expands complex work into tasks. |
| Assign subtask | `/sc:task "description" --owner <agent>` | Delegates work with ownership. |
| Implementation session | `/sc:implement --scope <path>` | Focused coding with guardrails. |
| Research & analysis | `/sc:analyze --topic "…"` | Collects context, risks, and open questions. |
| Test/quality gate | `/sc:test --suite cli` | Plans or executes validation. |
| Documentation update | `/update-docs:update-docs --paths <files>` | Keeps docs in sync. |
| Changelog entry | `/add-to-changelog:add-to-changelog "message"` | Records release note snippets. |
| Todo tracking | `/todo:todo add "task" [due]` | Maintains running task list. |

> **Tip:** Pair each agent mention (`@workflow-orchestrator`, `@research-analyst`, …) with the matching slash command so the assistant has persona and structure.

## Phase 0 – Kickoff & Alignment
```bash
/context-prime:context-prime
/initref:initref
/todo:todo add "Design new /sc:spec template command" next week
@workflow-orchestrator "Launch workstream for template-spec command"
/sc:spawn "Plan and deliver new template-spec command" --strategy adaptive --depth deep
```
1. Prime the workspace with current docs and file inventory.
2. Track the initiative in `todos.md` via the updated `/todo:todo` command.
3. Ask the orchestrator to expand the request into structured stories and tasks.

## Phase 1 – Research & Requirements
```bash
@research-analyst "Summarize existing template commands, gaps, and usage patterns"
/sc:analyze --topic "template command addition" --inputs "templates/claude/.claude/commands"
/sc:task "Produce acceptance criteria and guardrails" --owner research-analyst --deliverable docs/research/template-command-brief.md
```
- Review neighboring commands (e.g., `/sc:spec-panel`, `/sc:design`) to prevent overlap.
- Capture acceptance criteria, API surface, and failure cases in a research brief.
- Store the brief in `/ref` or `docs/research/` for downstream agents.

## Phase 2 – Design & Planning
```bash
@workflow-orchestrator "Translate research brief into implementation plan"
/sc:task "Outline command UX and payload schema" --owner workflow-orchestrator --deliverable docs/plans/template-spec-outline.md
/sc:design --artifact docs/plans/template-spec-outline.md --reviewers "documentation-engineer"
```
- Define command naming, slash syntax, argument validation, and output expectations.
- Validate dependencies (Rust embedding, tests, documentation) before work begins.

## Phase 3 – Implementation
```bash
@fullstack-developer "Implement the template-spec command per approved outline"
/sc:task "Scaffold command directory" --owner fullstack-developer --scope templates/claude/.claude/commands/spec
/sc:implement --scope templates/claude/.claude/commands/spec --checks lint
/sc:task "Embed command assets inside crates/ai-dlc-cli/embedded-templates" --owner fullstack-developer
```
- Create or modify markdown prompt files in the correct command directory.
- Run `scripts/sync-cli-templates.sh` to copy assets into the embedded bundle and rebuild the CLI.
- Keep commits atomic (scaffold, prompt content, embedded sync) for easier review.

## Phase 4 – Quality & Verification
```bash
@code-reviewer "Run quality gate for new template-spec command"
/sc:test --suite cli --notes "Validate ai-dlc-cli scaffold on fresh workspace"
/sc:task "Verify hidden .claude output includes new command" --owner code-reviewer --evidence logs/command-validation.md
```
- Execute targeted tests (Rust unit tests, `cargo run -- scaffold --provider claude`).
- Confirm `.claude/commands` output includes the new assets with correct naming.
- Document review notes, regression checks, and sign-off criteria.

## Phase 5 – Documentation & Comms
```bash
@documentation-engineer "Refresh docs for template-spec feature"
/update-docs:update-docs --paths README.md templates/workflows/template-extension-workflow.md
/add-to-changelog:add-to-changelog "feat(claude): add /sc:spec template authoring command"
@workflow-orchestrator "Prepare release announcement and merge checklist"
```
- Update README usage, workflow docs, and any provider-specific references.
- Log changelog items and ensure release tooling is aware of the new feature.

## Phase 6 – Handover & Continuous Improvement
```bash
@workflow-orchestrator "Close outstanding tasks and archive references"
/todo:todo complete 1
/sc:reflect --focus "template-spec rollout" --questions "What worked? What should change next time?"
```
- Close tracked todos and archive temporary research assets if appropriate.
- Hold a retrospective via `/sc:reflect` to capture lessons learned.

## Expected Artifacts
- `templates/claude/.claude/commands/<new-command>/` (or equivalent agent directory) with finalized prompt assets.
- Embedded template sync applied to `crates/ai-dlc-cli/embedded-templates/` (run `scripts/sync-cli-templates.sh`).
- Research brief, implementation outline, and validation logs stored in `docs/` or `/ref`.
- README/workflow updates and changelog entries referencing the new capability.

Following this workflow keeps multi-agent collaboration aligned with AI-DLC best practices while using the current slash command conventions.
