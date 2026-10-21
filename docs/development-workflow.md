# ai-dlc development workflow

Take a piece of work from an idea to an evidence-gated finish, and know which
stage owns which artifact along the way.

Tool names are kept in the [tool map](workflows/tool-map.md) so providers can
change without redefining the lifecycle. ai-dlc prepares tools, structure and
guidance for the chosen harness; agents invoke installed provider tools directly.

Use the [greenfield guide](workflows/greenfield.md) for a new application and the
[brownfield guide](workflows/brownfield.md) for an existing repository. The
[design-to-implementation guide](workflows/design-to-implementation.md) covers the
handoff from an approved design to code.

## Workflow at a glance

1. Intake and priority
2. Discovery
3. Product requirements
4. Product and technical design
5. Formal specification, when the design decides one is needed
6. Reviewed work record
7. Branch and implementation
8. Tests and required checks
9. Review and merge
10. Merged-revision CI evidence
11. Evidence-gated finish
12. Tracker completion and handoff

ai-dlc does not host an autonomous orchestrator. The human and agent decide
what work is useful; skills provide judgment, and the CLI validates, links and
gates the resulting work.

## Stage contracts

| Stage | Durable output | Exit condition |
| --- | --- | --- |
| Intake | Tracker item or reviewed candidate | The next investigation is explicit |
| Discovery | Bounded problem statement | The problem is clear enough to define or stop |
| Product requirements | Reviewed PRD when the change needs one | Material product questions are resolved or named |
| Design | Design document, diagram and linked decisions | Implementers can act without inventing product behavior |
| Specification decision | Recorded decision and, when required, provider-owned specification | Required scenarios and acceptance criteria are current |
| Work publication | `.ai-dlc/work/<id>.toml` and tracker item | The record is reviewed before external mutation |
| Implementation | Code, tests, migrations and updated durable docs | Local required checks pass |
| Review and merge | Reviewed pull request and merged revision | Review, repository rules and fresh checks pass against the current target branch |
| Verification and finish | CI receipts and optional deployment evidence | `ai-dlc work finish <work-id>` accepts every configured gate |
| Continuity | Handoff, runbook updates and linked personal notes | Remote state and remaining work are unambiguous |

Each stage consumes reviewed output from the previous stage. A stage may decide
an artifact is unnecessary; silently replacing it with assumptions is not allowed.

## Design to implementation ownership

Skills own discovery, requirements, design judgment and the specification
decision. The CLI owns reviewed work records, local checks, machine lifecycle
commands and completion gates; local MCP exposes a subset of them. The handoff
is complete only when the approved design, any required specification and the
reviewed work record let implementation proceed without inventing behavior.

## Environment preparation

Start a session with `ai-dlc next` (or `context --brief`) for local next
actions and required checks; it does not consult the tracker. The session-start
hook includes its first ten summary lines.

Use the [machine enrollment runbook](runbooks/machine-enrollment.md) for private
profiles, readiness and client setup, and the [GitHub](github-ticket-setup.md)
or [Jira](runbooks/jira-cloud-setup.md) runbook for the provider. The lifecycle
below stays independent of the selected provider.

### Explicit project commands

Setup steps, their optional `verify` commands, and `[checks.commands]` accept the same three forms:

```toml
[checks.commands]
legacy = "python scripts/check_tests.py"
portable = { argv = ["python", "scripts/check_tests.py"] }
windows = { shell = "powershell", script = "& python scripts/check_tests.py; exit $LASTEXITCODE" }
```

Strings keep their POSIX `sh -c` meaning on every OS. An argv record passes each
argument literally without shell expansion. Explicit shells are `posix` and
`powershell`; scripts must propagate native exit codes themselves. A missing
executable or shell is reported, never substituted.

The argv and shell forms
need an engine built after v0.4.0, and they do not make Windows a supported
host; see [release limits](release-verification.md).

## Sources of truth

- The repository owns architecture, product rationale, design context,
  decisions, runbooks, code, and tests.
- The configured specification provider exclusively owns formal behavior
  specifications. Repository design documents link to specifications instead
  of copying them.
- The selected delivery tracker owns engineering priority and lifecycle status.
  When an upstream business tracker is used, it owns business priority, outcome
  scope and acceptance; see
  [GitHub delivery with Jira outcomes](design/jira-cloud.md#github-delivery-with-jira-outcomes).
- SCM and CI own review, merge identity, and merged-revision evidence.
- Personal knowledge stores continuity, reflection, and private notes. It links
  durable repository material and is not a repository mirror.
- Portable configuration may name required environment variables, such as
  `token_env = "JIRA_API_TOKEN"`, but never contains their secret values.
  Machine configuration owns account choices and local paths; credential values
  stay in a keychain or secret injector and enter only the process environment.

When sources disagree, reconcile their owned facts; never overwrite one store
with a copy of another.

## Capability boundaries

Initialization and adoption may select any subset of `specs`, `tracker`,
`knowledge`, `scm`, `deploy`, and `agent-client`. Selection controls declared
roles and generated provider assets.

- Project setup, checks, architecture, design, decisions, and runbooks remain
  useful without external providers.
- The publish/start/finish lifecycle requires configured tracker and SCM roles;
  the tracker has no fallback. Omitting SCM also omits the generated GitHub
  workflow, so merged-revision CI completion is unavailable.
- `work status` inspects the local record without querying the tracker.
- Work that does not require a specification records `requires_spec = false`
  with a reviewed reason; work that does require one configures the role.
- Knowledge, deployment evidence, and agent clients are optional; deployment
  becomes a finish gate only when configured.

The [tool map](workflows/tool-map.md#role-to-provider-mapping) lists the
default provider for each role and the compatibility fallbacks.

Start team adoption with the repository's existing development commands. Select
the capabilities and clients it needs, choose shipped skills through
`agents.skills`, and put acceptance and regression commands in `checks.commands`
and `checks.required`. Scaffold checks are a starting point: a new Python
project's behavior test covers only its greeting output. Replace it with the
project's real acceptance and regression suite.

For edit feedback, run `ai-dlc project check --check CHECK_ID`, repeating
`--check` for more commands; they run in the requested order. A focused receipt
still lists every configured required check, so missing required outcomes cannot
pass the completion gate. Run the full required check after target-branch
integration, before merge. The
[brownfield behavior-check rehearsal](workflows/behavior-check.md)
covers adopting a team's existing checks.

## Daily operating loop

1. Reconcile tracker priority, work bindings, branch state, and fresh evidence.
2. Use discovery when the problem or outcome is unclear.
3. Draft and review product requirements when durable rationale is needed.
4. Produce the minimum design that closes product and technical ambiguity.
5. Record whether formal specification is required and make it current when it
   is.
6. Review the work record, then publish and start it through ai-dlc.
7. Implement on the bound branch with acceptance and regression tests.
8. Run `ai-dlc project check --required` before review.
9. Immediately before merge, update the branch from the target branch and rerun
   required checks; record documentation dispositions again only for targets the
   gate reports stale.
10. Merge through the configured SCM and finish through ai-dlc so the
    specification, merged revision, CI receipts and deployment evidence are
    checked together.
11. Update durable documentation and leave a concise handoff when continuity is
    needed.

## Completion is evidence-gated

`ai-dlc work finish <work-id>` is the completion boundary for projects with
tracker and SCM roles. It checks the authenticated merged revision rather than
the local checkout. The generated single-job GitHub workflow publishes
`ai-dlc-receipt`; matrix repositories declare every expected artifact in
`scm.receipt_artifacts`. A missing, malformed, dirty, mismatched, duplicate or
expired receipt blocks completion.

Tracker completion never substitutes for a merge, green CI, a current required
specification, or configured deployment evidence. Failures remain visible and
retryable instead of being converted into success.

### Changing the trusted service invalidates work bindings

A work record pins a fingerprint per provider role, so reviewed work cannot be
retargeted at a different service without an explicit review. The SCM
fingerprint covers the `[scm]` settings that decide which service is trusted:
`repository`, `target_branch` and `workflow`.

Changing any of them drifts the
bindings on every existing record, and `ai-dlc work finish` refuses with
`Provider binding drift` until each affected record is reviewed again.

`receipt_artifacts` is excluded: the finish gate reads expected receipt names
from `ai-dlc.toml` at the merged revision, so changing the CI matrix does not
drift bindings. Every other `[scm]` key contributes to identity.

When a binding drifts, review the affected records and remove the drifted
binding lines so they are recomputed against the current configuration. Do not
use `ai-dlc project rebind` for this; it migrates a role to a different
provider. Finished records keep their historical fingerprints.

### Finishing after the target branch moved

The specification gate reads the archived change from the working checkout. That
checkout must be exactly the pull request's merge commit with a clean
`openspec/` tree. Finishing immediately after merge satisfies this from the
updated main checkout. Once the target branch advances, use the explicit helper.

```sh
ai-dlc work finish <work-id> --at-merge
```

The helper resolves the bound PR through the selected SCM and needs its exact
merge commit available locally. It does not fetch, archive, repair CI or change
branches. It creates an owned detached checkout at that commit and runs ordinary
finish there, leaving the caller's HEAD, index and files untouched.
`--handoff FILE` and `--learning FILE` are read relative to the caller.

The result reports completion and cleanup separately. A blocked gate remains
blocked. If changes or an ownership mismatch prevent safe removal, the checkout
is retained and the recovery locator names it; inspect it before a nonforced
`git worktree remove`. Retrying finish reruns its gates through the same journal.

The manual fallback remains available:

1. `git worktree add --detach /tmp/finish-<work-id> <merge-commit>`
2. `cd /tmp/finish-<work-id> && ai-dlc work finish <work-id>`
3. `cd - && git worktree remove /tmp/finish-<work-id>`

Take the merge commit from the pull request the work record binds; the blocked
reason also names it. The gate is unchanged: a checkout that is not exactly the
merged revision, or one with modified `openspec/` files, still refuses.

## When a work record is needed

A work record binds reviewed scope to a tracker item, a branch and a pull
request. That binding lets `ai-dlc work finish` close the item against the
merged revision and its CI receipts. Create one when the change delivers a
tracker item or needs a formal specification.

No required check demands a record for every change. A change with no tracker
item and no specification decision needs only its pull request: a documentation
correction, a roadmap edit, a dependency bump. Put scope and verification in the
PR body and record documentation evidence under any identifier
(`--evidence-id <branch-or-topic>`).

A record created for such a change has
nothing to finish and stays open in the context brief indefinitely.

Projects selecting the optional `bound-push` hook also choose the rules for its
covered publication commands. Omitted `agents.bound_push_policy`, or explicit
`"all-branches"`, requires reviewed tracker-bound work even for the record-free
PR path above. A team may explicitly choose the lighter path in shared
`ai-dlc.toml`:

```toml
[agents]
bound_push_policy = "tracked-branches"
```

This setting does not enable the hook. When the hook is selected, it allows a
covered push or PR creation in two cases. Either the local inventory proves the
current branch unbound, or every matching work record is valid, reviewed,
tracker-bound and free of binding drift. Anything else blocks publication with a
repair instruction.

Only project configuration can set this policy. The hook covers supported native
tool payloads only and replaces none of the review, check or finish gates; the
[tool map](workflows/tool-map.md#optional-publication-hook) has the details.

## Merge against the current target branch

Documentation-impact decisions are stored per work item under
`.ai-dlc/documentation/evidence/<id>.json`. Each decision binds the content of
its own target and of the sources mapped to it; it does not name a target-branch
commit.

The gate computes changed files from the merge base of the CI comparison and
`HEAD`. A moved target branch therefore invalidates a decision only when it
changed content that the decision bound. Branches with disjoint changes merge
in either order with no evidence rewrite. Immediately before merging, do this.

1. Fetch and update the branch from the target branch.
2. Run `ai-dlc project check --required`. When `docs gate` reports a *stale*
   target it names the paths whose content differs. Review those and record that
   target again with `docs review --disposition ... --evidence-id <id>`, which
   keeps the decisions that remain valid. *Missing* targets need a first decision.
3. Push the update and wait for fresh required checks.

Pull request checks do not rerun when the target branch moves. A green check
can therefore predate a target change that touched bound content; the
target-branch run after merge then fails and names it.

To catch that before merge, enable the
branch protection option that requires branches to be up to date, with the
Verify jobs as required checks. ai-dlc does not change that setting.

Evidence files whose decisions no longer match any current target are inert;
`ai-dlc docs review --base <target> --prune` lists them and `--apply` removes
them. A project that still holds only schema 1
`.ai-dlc/documentation/current.json` must record that file again whenever the
target branch moves; the first per-work recording supersedes it.

Rules for editing this handbook are in
[CONTRIBUTING](https://github.com/Sean-Koval/ai-dlc/blob/main/CONTRIBUTING.md#maintaining-the-workflow-handbook).
