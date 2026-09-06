# Framework delivery: executor handoff

Objective: deliver the [approved direction](../product-direction.md) using the
dependency-ordered [roadmap](../roadmap.md). UI/UX is one optional part.

## Current state

- Main is merged through SAN-11 at `9b6ca29`. SAN-9, SAN-10, and SAN-11 are Done;
  their capability, readiness, and Linear onboarding changes are the active
  implementation baseline.
- SAN-12 is In Progress on `codex/portable-workflow-bundles`; Tasks 1–3
  implementation is committed through `ca5ab0a`. Manifest validation, pinned
  import preview/apply, and client/template distribution are implemented, but
  final review is not accepted and Task 4 closeout is blocked.
- Completed SAN-12 interfaces are duplicate-safe `validate_bundle`, shared
  `resolve_git_source`, context-managed `BundleCandidate`,
  `resolve_bundle`, `import_bundle`, and
  `ai-dlc agents bundle import SOURCE --ref REF --id ID [--apply
  --expected-commit SHA]`. Import vendors a deterministic lock and exact reviewed
  bytes transactionally; it does not activate, select, or render the bundle.
- Task 3 adds project-only `agents.bundles` selection, owned distribution to
  supported client skill directories and `docs/templates/`, a managed bundle
  guidance index, transaction-safe apply/rollback, byte-exact render checks, and
  structured bundle readiness with blocked-over-missing precedence. A fresh
  checkout can render and check vendored guidance with source, Git, and network
  access unavailable; no bundle content is executed.
- At `a6692c2`, the exact focused suite passed 725 tests. The required project gate
  passed all five outcomes with 1,119 tests and one expected unavailable-Cargo
  legacy skip. Formatting, lint, types, generated-file checks, strict OpenSpec
  validation, and patch hygiene were clean. These are local implementation
  checks, not merged-revision CI or live-service qualification.
- Fix commit `ca5ab0a` has pre-review local evidence of 739 focused tests and
  1,134 full tests passing. This evidence does not establish completion or final
  review acceptance.
- Final scoped re-review found that staged-file identity is not carried from
  creation through publication and cleanup. Staged bytes altered after creation
  can be published, and an authored file that replaces a stage path can be
  deleted during cleanup. An additional remediation decision is required before
  final review can be repeated.
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
2. Continue SAN-12 from `codex/portable-workflow-bundles` at fix commit
   `ca5ab0a`; do not restart from main or repeat the committed Tasks 1–3 scope.
3. Read `.ai-dlc/work/portable-workflow-bundles.toml`, the complete active
   OpenSpec change, and the exact execution plan. Confirm Linear remains the
   status authority before mutating tracker state.
4. Prepare with `sh scripts/bootstrap.sh --source`; use its printed PATH directories.
   Credentials are independently injected in the selected local environment.
5. Decide and implement an additional remediation that preserves staged-file
   identity from creation through publication and cleanup, preventing altered
   staged bytes from being published and authored stage-path replacements from
   being deleted.
6. Repeat final review after remediation. Only after acceptance may the OpenSpec
   change be archived, the PR/CI/merge evidence completed, and
   `ai-dlc work finish portable-workflow-bundles` run.
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
`ca5ab0aac702cc24876f596d9bf4f9a1c8389263` plus this documentation-only
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
- Checked Task 3 plan items reflect committed implementation and local evidence;
  they do not establish final review acceptance, merged-revision CI, or live
  qualification.

## Blockers and continuation

Current blocker: staged-file identity is not preserved from creation through
publication and cleanup, so altered staged bytes can be published and an authored
stage-path replacement can be deleted. OpenSpec archive, PR/CI/merge, and work
finish remain blocked pending an additional remediation decision and accepted
final review. Continue independent preparation when possible. Do not invent
evidence, reinterpret local fixtures as live qualification, waive v4 obligations,
or expand scope to make a blocker disappear.

Each handoff records work/ticket ID, branch/revision, delivered interfaces, spec and
plan links, actual verification outcomes, evidence locations, unresolved findings,
and next eligible task. The next agent should need those artifacts, not this chat.
