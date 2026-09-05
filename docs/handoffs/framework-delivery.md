# Framework delivery: executor handoff

Objective: deliver the [approved direction](../product-direction.md) using the
dependency-ordered [roadmap](../roadmap.md). UI/UX is one optional part.

## Current state

- Planning branch: `codex/design-pm-roadmap`.
- Implementation baseline: `241e715`, portable profile enrollment merged into main.
- This planning delivery adds documentation, specifications, work records, and
  sandbox ticket bindings. It does not implement the planned commands or skills.
- Original v4 change remains 10/14 tasks complete; missing release evidence is not waived.
- Machine enrollment was absent at the September 5 review. Project bootstrap and
  Linear health do not establish complete machine enrollment.
- See the planning ticket/PR for the final commit and fresh validation evidence.

## Start here

1. Read `AGENTS.md`, `ai-dlc.toml`, product direction, and the master plan.
2. Ensure the planning branch is reviewed and integrated before branching a feature
   from main; do not rely on missing uncommitted files.
3. Default first ticket: `component-capability-contract`.
   `product-shaping-workflow` is independently ready for a product-guidance owner.
4. Read the selected work record, whole OpenSpec change, and exact execution plan.
   Confirm current tracker status and completed dependencies before work.
5. Prepare with `sh scripts/bootstrap.sh --source`; use its printed PATH directories.
   Credentials are independently injected in the selected local environment.
6. Start/bind only the selected ticket using the branch procedure below. Implement one plan task at a time with
   regression evidence, source/generated updates, and scope review.
7. Complete focused and required checks, review, specification archive where
   required, PR/CI, merge, and `ai-dlc work finish <id>`.

### Exact first-ticket start

After the planning change is integrated and the checkout is clean and up to date,
use the existing commands below. The explicit branch link avoids the CLI's older
default `work/` branch prefix. Inject credentials through the selected environment;
these commands do not load a secret file automatically.

```sh
ai-dlc work link component-capability-contract branch codex/component-capability-contract
ai-dlc work start component-capability-contract
```

For a different ready ticket, substitute its work ID in both commands and use
`codex/<work-id>` for its branch. Do not republish an already bound ticket to edit
its title or description: publishing is reconciliation, not a metadata editor.

## Invariants

- The harness can use installed tools directly; AI-DLC makes the workflow available
  and consistent while preserving configured checks and finish policy.
- Tool selection connects to installation, configuration, instructions, and readiness.
- Product evidence differs from hypotheses. Specifications define behavior;
  tickets organize deliverable slices; checkboxes describe implementation steps.
- Credentials never enter tracked files, output, or tickets. Provider changes do
  not silently redirect existing work.
- Do not add future `depends_on`/`requirements` fields to current Work records
  until the traceability ticket supports them. Check plans and Linear relationships.
- Sample regressions and expected new files in plans are future implementation
  instructions, not evidence that those tests exist or have passed.

## Blockers and continuation

Report the exact blocker if an accepted interface conflicts with current behavior,
a dependency is unfinished, a live target is unavailable, or human ratings/budget
are absent. Continue independent preparation when possible. Do not invent evidence
or expand scope to make a blocker disappear.

Each handoff records work/ticket ID, branch/revision, delivered interfaces, spec and
plan links, actual verification outcomes, evidence locations, unresolved findings,
and next eligible task. The next agent should need those artifacts, not this chat.
