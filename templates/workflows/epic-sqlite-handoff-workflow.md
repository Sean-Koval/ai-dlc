# Epic Workflow: Agent Work Sharing via SQLite MCP Hub

## Goal
Deliver an end-to-end capability that lets CLAUDE agents persist and exchange work artifacts through shared SQLite `.db` files inside a collaborative folder, with a dedicated MCP server mediating access. This workflow covers epic discovery, design iteration, phased delivery, sub-feature execution, validation, documentation, and deployment—using only non-`sc_commands` tooling.

## Core Personas & Supports
- **workflow-orchestrator** – overall conductor tracking phases, dependencies, and handoffs (`templates/claude/.claude/agents/09-meta-orchestration/workflow-orchestrator.md`).
- **research-analyst** – explores user stories, competitive patterns, and risks (`templates/claude/.claude/agents/10-research-analysis/research-analyst.md`).
- **systems-architect** – designs storage, synchronization, and security patterns (`templates/claude/.claude/agents/03-infrastructure/platform-engineer.md` or similar).
- **fullstack-developer** – implements CLI/template changes and MCP integration (`templates/claude/.claude/agents/01-core-development/fullstack-developer.md`).
- **documentation-engineer** – maintains docs and internal references (`templates/claude/.claude/agents/06-developer-experience/documentation-engineer.md`).
- **code-reviewer** – enforces quality gates and regression coverage (`templates/claude/.claude/agents/04-quality-security/code-reviewer.md`).
- **deployment-engineer** – prepares release artifacts and rollout plans (`templates/claude/.claude/agents/03-infrastructure/deployment-engineer.md`).

## Command Palette (non `sc_commands`)
| Purpose | Command | Expected Output | Validation & Next-Step Usage |
| --- | --- | --- | --- |
| Prime repo understanding | `/context-prime:context-prime` | Conversation snippet summarizing README, key directories, recent files | Product manager verifies important docs surfaced; developers note gaps. If context missing, manually open docs and re-run. Approved summary seeds discovery prompts. |
| Generate reference dossiers | `/initref:initref` | Refreshed `/ref/*.md` summaries | Systems architect confirms core components documented; missing modules trigger follow-up manual summaries before design starts. |
| Create PAC epic | `/project-management:pac-create-epic "Agent SQLite handoff" --owner core-platform` | `.pac/epics/epic-agent-sqlite-handoff.yaml` plus branch suggestion | PM inspects metadata (scope, success metrics). If incorrect, rerun with flags or edit file. Epic ID used when linking subsequent features/tasks. |
| Draft PRP / PRD | `/project-management:create-prp "Agent handoff" --research` & `/project-management:create-prd "Agent handoff"` | `product-development/current-feature/PRP.md` & `PRD.md` populated | PM ensures personas, acceptance criteria, success metrics present; architect validates constraints. If sections thin, provide more context and rerun before decomposition. |
| Brainstorm & backlog | `/project-management:create-feature "<feature>"` | Feature YAML/markdown (PAC) capturing scope & owner | Orchestrator checks mapping to epic goals; developers confirm feasibility. If features missing, iterate before orchestration. |
| Maintain todos & checkpoints | `/todo:todo ...` | Updated `todos.md` with numbered items & due dates | All roles ensure tasks reflect current plan. Unclear todos are rewritten before proceeding; list is reviewed at phase gates. |
| Orchestrate large task boards | `/orchestrate --focus agent-collaboration` | `/task-orchestration/<date>/...` tree with MASTER-COORDINATION.md, trackers | Workflow-orchestrator verifies tasks cover full backlog; QA ensures QA tasks exist. If output incomplete, add manual tasks then continue. |
| Check status midstream | `/task-status --detailed` | Status report (counts, per-task details) | Used in stand-ups; blockers converted to new todos. If stale, rerun /orchestrate to refresh plan. |
| Deep documentation audit | `/documentation:docs-maintenance --audit "agent handoff ecosystem"` | Audit log listing stale docs, owners, remediation steps | Documentation engineer converts high-priority issues into todos; unresolved audit items block later release. |
| Update implementation docs | `/update-docs:update-docs` | Edited docs with inline notes highlighting updates | Documentation engineer reviews diff; PM spot-checks accuracy. Docs become reference for QA and enablement. |
| Manage changelog | `/add-to-changelog:add-to-changelog "message"` | Entry appended to CHANGELOG.md | Release manager validates formatting; entries referenced in release plan. |
| Commit changes | `/commit:commit` | Conventional commit(s) created/pushed | Developers inspect staged diff; if command reports no staged changes, stage manually and rerun. Commits referenced in PR creation. |
| Prepare PR | `/create-pr:create-pr` | Branch push, formatted PR body, test plan | Developer ensures PR links back to epic/feature docs; missing context added before requesting review. |
| Trigger review | `/pr-review:pr-review` | Structured checklist covering tests, docs, risks | QA/compliance confirm all checks pass; failing sections spawn follow-up todos before merge. |
| Build release note | `/release:release` | CHANGELOG + version bump recommendation | Release engineer confirms semver and narrative; updates published after deployment. |
| Testing strategy | `/testing_plan_integration:testing_plan_integration "<scope>"` | Proposed integration test list awaiting approval | QA reviews and edits before implementation. Tests feed execution in verification phase. |
| Operational readiness | `/deployment:prepare-release --scope "agent handoff"` | Deployment checklist detailing rollout, rollback, comms | Deployment engineer confirms items complete; unresolved steps block release. |

> Pair agent mentions with these commands so the assistant receives both persona context and structured instructions.

---

## Phase 0 – Epic Kickoff & Context Loading
```bash
/context-prime:context-prime
/initref:initref
/todo:todo add "Epic: Enable agent handoff via SQLite MCP" today
@workflow-orchestrator "Open epic workspace for agent handoff program"
/project-management:pac-create-epic "Agent collaboration via SQLite MCP" --owner platform --scope "Persistent shared storage + MCP interface"
```
**Expected outputs & checks**
- `/context-prime` transcript lists README highlights, key directories (e.g., `crates/`, `templates/`), and recent commits. *Product manager* ensures nothing critical is missing; if it is, open the file manually, then rerun for updated context.
- `/initref` writes refreshed summaries into `/ref/`. *Systems architect* scans for accuracy; missing modules get added via manual notes before design conversations.
- `/todo:todo` appends a numbered entry to `todos.md`. *Workflow-orchestrator* confirms ordering/due date; if numbering off, fix file before proceeding.
- Orchestrator acknowledgement should outline immediate next actions (e.g., “prepare PRP/PRD”). If absent, provide additional instruction and reiterate goal.
- `/project-management:pac-create-epic` must create `.pac/epics/epic-agent-collaboration-via-sqlite-mcp.yaml` with owner/scope/success metrics. *Product manager* reviews metadata; incorrect details are edited or the command is rerun with richer arguments.

**Next-phase inputs**
- The context transcript and `/ref` summaries are referenced when drafting PRP/PRD.
- The PAC epic ID anchors feature creation and orchestration folder names.
- `todos.md` entry is used to track epic status in later stand-ups.

## Phase 1 – Discovery, Brainstorming, and Vision
```bash
@research-analyst "Gather user stories for collaborative agent handoff" 
/project-management:create-prp "Agent handoff" --research
/project-management:create-prd "Agent handoff" 
/documentation:docs-maintenance --audit "agent collaboration background"
```
**Expected outputs & checks**
- Research analyst produces a narrative with personas, scenarios, risks. *Product manager* reviews completeness; if specific use cases (e.g., multi-agent queue handoff) missing, provide follow-up prompt and iterate.
- `/project-management:create-prp` writes `product-development/current-feature/PRP.md`. Ensure sections for problem statement, desired outcomes, guardrails are filled. *Architect* highlights any unclear constraints; iterate until crisp.
- `/project-management:create-prd` creates `PRD.md` including KPIs, acceptance criteria, dependency map. *PM* and *architect* jointly sign off; unresolved questions go into `todos.md` before moving forward.
- `/documentation:docs-maintenance --audit ...` outputs an audit log citing outdated docs. *Documentation engineer* copies high-priority items into `todos.md` and flags blockers. If command cannot locate docs, supply directories via arguments and rerun.

**Next-phase inputs**
- PRP and PRD feed the architecture brief in Phase 2.
- Research narrative supplies user stories for feature decomposition.
- Audit results inform which docs must be refreshed during each sub-feature delivery.

## Phase 2 – Epic Design & Decomposition
```bash
@systems-architect "Design SQLite schema + MCP interaction model"
/project-management:create-feature "shared-storage-schema"
/project-management:create-feature "mcp-bridge-service"
/project-management:create-feature "agent-tooling-updates"
/project-management:create-feature "cli-sync-automation"
/orchestrate --focus agent-collaboration
/todo:todo add "Define sync conflict resolution" tomorrow
```
**Expected outputs & checks**
- Architect returns an outline describing shared folder layout, SQLite schema versioning, MCP API (methods, auth). Store in `docs/epics/agent-handoff.md`. If locking or offline flow not addressed, prompt for addendum.
- Each `/project-management:create-feature` command emits feature metadata (type, owner). *Workflow-orchestrator* ensures owners match functional leads and scope text is non-empty. Missing info is backfilled before continuing.
- `/orchestrate` generates `/task-orchestration/<date>/agent-collaboration/...` with MASTER-COORDINATION.md. *Orchestrator* checks stories map to features; *QA* ensures QA/integration tasks exist. If tree absent, rerun with clearer task list input.
- `/todo:todo` entry tracks design follow-up. *PM* validates due date relative to sprint timeline.

**Next-phase inputs**
- Architecture doc feeds feature design sessions.
- Orchestration board provides the canonical task backlog; referenced by `/task-status` in subsequent phases.
- Feature metadata ties commits/PRs back to PAC for traceability.

### Suggested Epic Artifacts
- **Architecture Blueprint:** ER diagrams, file locking strategy, MCP API contract.
- **Risk Register:** concurrency, corruption, access controls.
- **Success Metrics:** handoff latency, conflict resolution accuracy, audit logging completeness.

---

## Phase 3 – Feature Execution Loop
For each feature (`shared-storage-schema`, `mcp-bridge-service`, `agent-tooling-updates`, `cli-sync-automation`), iterate through the AI-DLC feature lifecycle. The pattern below can be reused by updating arguments/paths.

### 3.1 Feature Kickoff
```bash
/todo:todo add "Feature: shared-storage-schema" today
/project-management:create-feature "shared-storage-schema" --type "backend" --owner data-platform
@workflow-orchestrator "Sequence tasks for shared-storage-schema"
/orchestrate --focus shared-storage-schema
```
**Expected outputs & checks**
- `todos.md` reflects the new feature entry with due date; *orchestrator* ensures numbering stays sequential. If duplication occurs, adjust manually.
- PAC feature updated with type/owner; *PM* verifies alignment with resource plan.
- Orchestrator response lists subtasks (schema design, migrations, tests). If vague, provide more context about desired deliverables and rerun.
- `/orchestrate` creates feature-specific coordination folder under `/task-orchestration/<date>/shared-storage-schema/`. Verify TODO/In Progress/QA directories exist. Missing folders should be created manually before work begins.

**Next-phase inputs**
- The orchestration tracker becomes the authoritative task list for design and implementation steps.
- Todo entry is reviewed during stand-ups and at feature exit criteria.

### 3.2 Design & Planning
```bash
@systems-architect "Finalize SQLite schema and migration plan"
/todo:todo add "Draft schema doc" today
/update-docs:update-docs
```
**Expected outputs & checks**
- Architect response should include table definitions, indexes, conflict handling, and migration approach. Missing pieces trigger a follow-up question before coding.
- Todo entry references the documentation file path; *documentation-engineer* ensures task remains open until doc merged.
- `/update-docs` updates `docs/design/shared-storage-schema.md` (or creates it). *PM* reviews diff for clarity; *developer* confirms implementation notes are actionable. If command fails to locate file, create stub manually and rerun.

**Next-phase inputs**
- Schema doc informs implementation steps (SQL scripts, Rust migrations).
- Todo reminds team to revisit doc if changes occur mid-implementation.

### 3.3 Implementation Sprint
```bash
@fullstack-developer "Implement shared storage feature"
/act:act
/commit:commit
/todo:todo add "Run schema smoke tests" today
```
**Expected outputs & checks**
- Developer outlines step-by-step plan (update migrations, adjust embedded templates, run tests). If plan missing, ask for explicit checklist before coding.
- `/act:act` should report completion of RED → GREEN → REFACTOR cycle. If interrupts mid-cycle, rerun after addressing issues.
- `/commit:commit` must create a conventional commit. Review the diff to ensure only intended files included; if tool suggests splitting commits, follow guidance before proceeding.
- Todo entry ensures smoke tests run later; *QA* checks presence.
- Developers manually run `scripts/sync-cli-templates.sh` + `cargo build` and attach notes to orchestration tracker; if build fails, resolve before moving to verification.

**Next-phase inputs**
- Commit hash referenced in PR stage.
- Smoke-test todo triggers execution during verification.

### 3.4 Verification
```bash
@code-reviewer "Evaluate shared storage implementation"
/testing_plan_integration:testing_plan_integration "shared-storage-schema"
/todo:todo add "Address review feedback" tomorrow
```
**Expected outputs & checks**
- Reviewer response contains detailed comments (bugs, style, risk). *Developer* logs resulting tasks in orchestration tracker; if response is empty, request explicit confirmation tests were run.
- `/testing_plan_integration` proposes named tests (e.g., `test_shared_db_insert`, `test_conflict_resolution`). *QA* approves or amends plan before tests implemented. Missing critical paths require additional prompts.
- Todo ensures follow-up on review items. Completion of this todo is required before documentation phase.
- Execute smoke/integration tests (CLI scaffold, concurrent agent simulation); attach logs under `logs/agent-handoff/`. Failing tests reopen implementation phase.

**Next-phase inputs**
- Approved test list referenced in PR description and release notes.
- Review findings inform doc updates and changelog entries.

### 3.5 Documentation & Merge Prep
```bash
@documentation-engineer "Update docs for shared storage"
/update-docs:update-docs
/add-to-changelog:add-to-changelog "feat: add shared SQLite storage foundation"
/commit:commit
/create-pr:create-pr
/pr-review:pr-review
```
**Expected outputs & checks**
- Documentation engineer outlines which files to edit (README, architecture doc, workflow). *PM* confirms coverage.
- `/update-docs` produces updated markdown; reviewer inspects diff for accuracy and links back to PRD.
- `/add-to-changelog` appends formatted entry. *Release manager* validates scope tag (`feat`, `docs`, etc.).
- `/commit:commit` captures doc changes; verify only documentation files staged.
- `/create-pr` uploads branch, generates PR body referencing PRP/PRD/test plan. If missing links, edit PR description manually.
- `/pr-review` triggers checklist; *QA* ensures tests listed earlier are reflected in the review summary.

**Next-phase inputs**
- PR URL logged in orchestration tracker and changelog for traceability.
- Checklist results used to decide if feature is ready to merge; failing items reopen implementation.

### 3.6 Repeat for Remaining Features
Adjust the target artifact paths and testing focus:
- **mcp-bridge-service:** define protocol, implement MCP server, add CLI config.
- **agent-tooling-updates:** update `.claude/commands` and `.claude/agents` to consume the shared DB.
- **cli-sync-automation:** add Rust CLI commands/scripts to sync or reconcile data; ensure embedded templates updated.

For each feature, expect the same pattern of outputs (design doc, commits, test plan, docs, PR). *Workflow-orchestrator* cross-references MASTER-COORDINATION.md to ensure no feature exits without passing documentation + review gates. If a feature stalls, use `/task-status --status on_hold` to surface blockers and create remediation todos before proceeding.

Use `/task-status --detailed` to resume work after breaks, referencing outstanding TODOs and orchestration tasks.

---

## Phase 4 – Integration & System Testing
```bash
@workflow-orchestrator "Coordinate cross-feature validation"
/orchestrate --focus "integration testing"
/testing_plan_integration:testing_plan_integration "Agent handoff end-to-end"
/todo:todo add "Record integration test outcomes" today
```
**Expected outputs & checks**
- Orchestrator response should list integration tasks (multi-agent simulation, concurrent writes, recovery drills). If absent, provide scenario details and rerun.
- `/orchestrate` creates a new subfolder for integration efforts; verify tasks encompass every feature. Missing tasks are added manually.
- `/testing_plan_integration` outputs consolidated test plan referencing prior feature tests plus new cross-cutting scenarios. *QA lead* approves plan before execution.
- Todo entry reminds team to store results (logs, screenshots). Ensure completion before exit criteria.
- Execute tests: run CLI to scaffold, simulate agent interactions via MCP server, validate `.db` contents. Failures must be logged and resolved; only proceed when tests pass.

**Next-phase inputs**
- Integration logs become attachments in release notes.
- Approved test list referenced during PR review for final merge approvals.

## Phase 5 – Documentation, Playbooks, and Enablement
```bash
@documentation-engineer "Publish agent handoff playbook"
/update-docs:update-docs
/documentation:docs-maintenance --optimize "agent handoff rollout"
/add-to-changelog:add-to-changelog "docs: add agent handoff epic playbook"
```
**Expected outputs & checks**
- Playbook outline (folder structure, data lifecycle, troubleshooting). *PM* ensures instructions match PRD scenarios.
- `/update-docs` updates README/workflow files; confirm cross-links (e.g., to this workflow) exist.
- `/documentation:docs-maintenance --optimize` lists improvements (e.g., diagrams). High-priority recommendations converted to todos.
- `/add-to-changelog` records documentation update entry for transparency.

**Next-phase inputs**
- Playbook referenced by deployment and enablement teams during rollout.
- Documentation updates cited in release notes and developer onboarding.

## Phase 6 – Release Packaging & Deployment
```bash
/deployment:prepare-release --scope "agent handoff"
/release:release
/add-to-changelog:add-to-changelog "release: agent handoff epic"
```
**Expected outputs & checks**
- `/deployment:prepare-release` produces checklist (migration steps, backfill, comms). *Deployment engineer* ensures each item marked complete; unresolved tasks block release.
- `/release:release` suggests version bump and change summary. *Release manager* confirms semver rules; if incorrect, adjust manually.
- `/add-to-changelog` records final release entry referencing tag/version.
- Build artifacts (`cargo build --release`, npm pack) generated manually; attach artifact links in checklist. Failures require remediation before proceeding.

**Next-phase inputs**
- Release checklist statuses feed post-launch health review.
- Changelog entry used for announcement emails and documentation updates.

## Phase 7 – Post-Launch Monitoring & Continuous Improvement
```bash
/task-status --detailed --today
/todo:todo add "Collect adoption metrics" next week
/project-management:project-health-check "agent handoff"
```
**Expected outputs & checks**
- `/task-status` report should show zero critical blockers; if items remain, reopen relevant feature loop before closing epic.
- Todo entry captures follow-up (metrics, feedback collection). *PM* ensures due date aligns with monitoring cadence.
- `/project-management:project-health-check` outputs health assessment (status, risks, actions). *Leadership* reviews; unresolved risks become new features/todos.
- Schedule retrospective; record notes in `docs/retros/agent-handoff.md`. Missing retro notes signals process gap.

**Next-phase inputs**
- Health report and retro notes inform future epics and backlog grooming.
- Adoption metrics todo ensures post-launch tracking kicks off.

---

## Break/Resume Best Practices
- Before pausing, run `/task-status --detailed` and `/todo:todo list` to capture current state; store summary in MASTER-COORDINATION.md so next session starts with context.
- Commit or stash WIP; use `/add-to-changelog:add-to-changelog "wip: context"` or append notes to `docs/journal/agent-handoff.md` so future contributors understand remaining work.
- On resumption, replay `/context-prime:context-prime` (to refresh documentation in memory) and review orchestration tracker tasks marked `in_progress` or `on_hold`. Any unclear tasks should be clarified before coding resumes.

## Final Deliverables Checklist
- [ ] PAC epic + features tracked in `.pac/`
- [ ] Architecture docs, PRP, PRD, and risk register stored in `docs/`
- [ ] Updated `.claude/commands`/`.claude/agents` and embedded templates
- [ ] MCP server implementation with integration tests
- [ ] CLI commands for sync and reconciliation
- [ ] README/workflow documentation additions
- [ ] Changelog and release notes published
- [ ] Monitoring hooks and adoption metrics defined

Following this epic workflow keeps large-scale initiatives aligned with AI-DLC practices, ensures continuity across breaks, and delivers production-ready capabilities through deliberate, audited phases.
