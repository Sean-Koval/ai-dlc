# Framework delivery: executor handoff

Objective: deliver the [approved direction](../product-direction.md) using the
dependency-ordered [roadmap](../roadmap.md). UI/UX is one optional part.

## Current state

- Main is merged through SAN-11 at `9b6ca29`. SAN-9, SAN-10, and SAN-11 are Done;
  their capability, readiness, and Linear onboarding changes are the active
  implementation baseline.
- SAN-12 is In Progress on `codex/portable-workflow-bundles`; implementation is
  complete through `72aa6d6`. Manifest validation and pinned import preview/apply
  (Tasks 1 and 2) are complete. Client/template distribution and closeout (Tasks
  3 and 4) remain.
- Completed SAN-12 interfaces are duplicate-safe `validate_bundle`, shared
  `resolve_git_source`, context-managed `BundleCandidate`,
  `resolve_bundle`, `import_bundle`, and
  `ai-dlc agents bundle import SOURCE --ref REF --id ID [--apply
  --expected-commit SHA]`. Import vendors a deterministic lock and exact reviewed
  bytes transactionally; it does not activate, select, or render the bundle.
- At `72aa6d6`, the Task 2 suite passed 116 tests, the exact focused suite passed
  695 tests, and the required project gate passed all five outcomes with 1,090
  tests. Formatting, lint, types, generated-file checks, strict OpenSpec
  validation, and patch hygiene were clean. These are local implementation
  checks, not merged-revision CI or live-service qualification.
- The original v4 change remains 10/14 tasks complete; missing release evidence
  is not waived. Its clean-machine, container, hosted-client, live provider,
  behavioral-evaluation, and release-artifact obligations remain governed by
  [release verification](../release-verification.md).
- Machine enrollment was absent at the September 5 review. Project bootstrap and
  Linear health do not establish complete machine enrollment.
- The original planning evidence remains at
  [framework delivery review](../planning/framework-delivery-review.md); its old
  backlog snapshot is historical evidence, not current ticket status.

## Start here

1. Read `AGENTS.md`, `ai-dlc.toml`, product direction, and the master plan.
2. Continue SAN-12 from `codex/portable-workflow-bundles`, whose implementation
   baseline is `72aa6d6`; do not restart from main or repeat completed Tasks 1
   and 2.
3. Read `.ai-dlc/work/portable-workflow-bundles.toml`, the complete active
   OpenSpec change, and the exact execution plan. Confirm Linear remains the
   status authority before mutating tracker state.
4. Prepare with `sh scripts/bootstrap.sh --source`; use its printed PATH directories.
   Credentials are independently injected in the selected local environment.
5. Implement Task 3 only: add project-only `agents.bundles` validation; distribute
   selected vendored skills, templates, and the managed guidance index through
   existing ownership/rendering; add bundle-aware readiness; and prove a fresh
   checkout works with the source unavailable and every Git/network seam blocked.
6. Complete Task 4 only after Task 3 review: run focused and required checks,
   validate and archive the OpenSpec change, link PR/CI and merged-revision
   evidence, then run `ai-dlc work finish portable-workflow-bundles`.
7. Continue with SAN-13 after SAN-12 closeout. SAN-13 remains independently ready
   for a product-guidance owner; the other five unstarted tickets follow the
   dependency graph in the roadmap.

### Exact SAN-12 continuation

Confirm the branch and baseline before editing:

```sh
git branch --show-current
git rev-parse HEAD
ai-dlc work status portable-workflow-bundles
```

Expected Git state at this handoff is branch `codex/portable-workflow-bundles`
containing implementation revision
`72aa6d6fe5927a335cc657162cfd36099f66ecf1` plus this documentation-only
synchronization. Do not relink, restart, or republish the already active work
merely to edit tracker metadata: publication is reconciliation, not a metadata
editor.

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
- Unchecked Task 3 regressions and expected files in the plan are implementation
  instructions, not evidence that those tests exist or have passed.

## Blockers and continuation

Report the exact blocker if Task 3 conflicts with a completed Task 1/2 interface,
a dependency is unfinished, a live target is unavailable, machine enrollment is
still absent where required, or human ratings/budget are absent. Continue
independent preparation when possible. Do not invent evidence, reinterpret local
fixtures as live qualification, waive v4 obligations, or expand scope to make a
blocker disappear.

Each handoff records work/ticket ID, branch/revision, delivered interfaces, spec and
plan links, actual verification outcomes, evidence locations, unresolved findings,
and next eligible task. The next agent should need those artifacts, not this chat.
