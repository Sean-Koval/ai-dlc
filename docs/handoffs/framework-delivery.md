# Framework delivery: executor handoff

Objective: deliver the [approved direction](../product-direction.md) using the
dependency-ordered [roadmap](../roadmap.md). UI/UX is one optional part.

## Current state

- Main is merged through SAN-11 at `9b6ca29`. SAN-9, SAN-10, and SAN-11 are Done;
  their capability, readiness, and Linear onboarding changes are the active
  implementation baseline.
- SAN-12's last known tracker state is In Progress on
  `codex/portable-workflow-bundles`; Tasks 1–3 implementation includes `19809bc`
  and scoped stage-retention repair `83d0718`. Manifest validation, pinned
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
- The user-authorized remediation at `19809bc` carries stage identity and expected
  bytes from creation through publication and cleanup. It fixes both original
  reproductions and has pre-review local evidence of 741 focused tests and 1,136
  full tests passing, with all five required outcomes passing. This evidence does
  not establish completion or final review acceptance.
- The review of `19809bc` rejected completion: cleanup verifies a stage and then
  separately unlinks its pathname, so an authored replacement arriving between
  verification and unlink can be deleted. That cycle was followed by renewed
  maintainer authorization on September 6.
- The renewed TDD remediation removes failed-stage deletion entirely. Complete,
  partial, and rollback-displaced stages are retained, and their filenames/paths
  are reported on the original failure. Recovery retries preserve notes from
  secondary failures. This is conservative retention, not atomic deletion.
- Independent review accepts the scoped stage-retention repair, with no remaining
  findings in that diff. Whole SAN-12 acceptance is still blocked: the separate
  successful-transaction backup cleanup path checks identity then unlinks by name.
  See the [cycle report](../planning/stage-cleanup-review-2026-09-06.md).
- Final local evidence for `83d0718`: 746 focused tests and 1,141 full tests
  passed; all five required project outcomes, strict OpenSpec validation, and
  patch hygiene passed. These runs tested the repair before commit and do not
  establish merged-revision CI or live-platform qualification. Task 4.1 is
  checked; the combined review/archive/PR/finish item remains unchecked.
- Fresh Linear status could not be read because `LINEAR_SANDBOX_TOKEN` was absent.
  No tracker mutation, OpenSpec archive, PR, merge, or work finish was attempted.
- The requested personal/work provider split is recorded in the
  [substitution assessment](../planning/provider-substitution-2026-09-06.md):
  Plane for personal tickets, Jira for work tickets, Confluence for team document
  publication, and Obsidian retained for viewing/private notes. Adapters and
  publication contracts are not implemented; existing bindings remain unchanged.
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
2. Continue SAN-12 from the current `codex/portable-workflow-bundles` head,
   including the scoped retention fix; do not restart from main or repeat Tasks 1–3
   scope.
3. Read `.ai-dlc/work/portable-workflow-bundles.toml`, the complete active
   OpenSpec change, and the exact execution plan. Confirm Linear remains the
   status authority before mutating tracker state.
4. Prepare with `sh scripts/bootstrap.sh --source`; use its printed PATH directories.
   Credentials are independently injected in the selected local environment.
5. Resolve the separate successful-backup cleanup design/scope. The renewed
   failed-stage remediation and review cycle is complete; it does not authorize
   a broader staging lifecycle redesign or establish whole-change acceptance.
6. Only after an authorized remediation and accepted final review may the
   OpenSpec change be archived, the PR/CI/merge evidence completed, and
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
containing stage-retention repair `83d0718` after baseline `ab1f15b` and its
documentation synchronization. Do not relink, restart, or republish active work
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

Current blocker: successful-transaction backup cleanup still separately checks
identity and unlinks the pathname. The scoped failed-stage repair is independently
accepted; it retains residue rather than deleting it. Inspect reported files with
concurrent writers stopped and preserve authored content before manual removal.
Do not bulk-delete `.ai-dlc-*` by filename pattern.
OpenSpec archive, PR/CI/merge, and work finish remain blocked on whole-change
acceptance and a decision on the remaining cleanup boundary. Continue preparation
when possible. Do not invent evidence, reinterpret local fixtures as live
qualification, waive v4 obligations, or expand scope to make a blocker disappear.

Each handoff records work/ticket ID, branch/revision, delivered interfaces, spec and
plan links, actual verification outcomes, evidence locations, unresolved findings,
and next eligible task. The next agent should need those artifacts, not this chat.
