# Framework delivery: executor handoff

Current completion: GitHub #18 finished through AI-DLC at merged `631d10a`.
PR [#25](https://github.com/Sean-Koval/ai-dlc/pull/25) merged at
`ab6b7743b435d63848bb45affd1be7eb6229b395`; all five platform jobs supplied
passing exact merged-revision receipts. A fresh GitHub clone completed source
bootstrap and AI-DLC finish for #10 and #11. Both issues are Completed and their
Project items are Done. Native harness/shared connection children are delivered
in that PR; parent #19 remains open for toolset and connection composition.

The next integrated branch is `codex/work-computer-toolsets`: reviewed #12,
toolset/native composition, Jira new-work onboarding, credential readiness,
bootstrap reliability and qualification-record validation. Plane, optional Design
PM guidance and calibration preparation are under final independent review.
Individual candidates passed required checks. The first combined full run failed
three tests during disk pressure, including two explicit out-of-space errors;
its passing first four checks do not make it a successful full run. The reviewed
packaging repair excludes compiled Rust outputs while retaining historical source.
Final integrated checks, archives, PR and merged-CI finish remain pending.

## Current authority — September 7

Start with [current roadmap](../roadmap.md),
[current execution plan](../superpowers/plans/2026-09-07-work-computer-readiness.md)
and [GitHub Project](https://github.com/users/Sean-Koval/projects/2). GitHub owns
priority/status. Project authorization, linking and eight local mappings are
complete in PR #23. The current goal is work-computer adoption with Claude and
Antigravity, Jira Cloud for new work, and private Obsidian notes. Antigravity
project files are implemented locally; actual-client qualification remains open.
Confluence remains deferred.

The historical executor notes below preserve the separate SAN-12 branch and
prior evidence; their old Linear-first sequence/access assumptions do not define
the next task. Follow the current candidate and issue matrix above; do not restart
completed predecessors or revive old cleanup instructions.


Objective: deliver the [approved direction](../product-direction.md) using the
dependency-ordered [roadmap](../roadmap.md). UI/UX is one optional part.

## Historical September 5 state

- Planning branch: `codex/design-pm-roadmap`.
- Planning review: [PR #5](https://github.com/Sean-Koval/ai-dlc/pull/5), draft at
  handoff; [validation evidence](../planning/framework-delivery-review.md).
- Implementation baseline: `241e715`, portable profile enrollment merged into main.
- This planning delivery adds documentation, specifications, work records, and
  sandbox ticket bindings. It does not implement the planned commands or skills.
- Original v4 change remains 10/14 tasks complete; missing release evidence is not waived.
- Machine enrollment was absent at the September 5 review. Project bootstrap and
  Linear health do not establish complete machine enrollment.
- See the planning ticket/PR for the final commit and fresh validation evidence.

## Historical executor procedure

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
