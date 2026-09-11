# AI-DLC development workflow

This is the canonical, compact map of the AI-DLC workflow. It describes stable
development stages and their evidence contracts. Tool names are kept in the
[tool map](workflows/tool-map.md) so providers can change without redefining the
lifecycle.

AI-DLC prepares tools, structure, and guidance for the chosen harness. Agents can
invoke installed provider tools directly. The services below own specific
validation and lifecycle boundaries; they do not mediate every development action.
See [product direction](product-direction.md) and the [roadmap](roadmap.md) for
planned capabilities.

Product requirements explain outcomes, specifications define behavior, tickets
organize deliverable slices, and tasks describe implementation steps. Link these
artifacts through stable references. UI/UX evaluation is an optional branch;
other work uses its own appropriate verification methods.

Use the [greenfield guide](workflows/greenfield.md) for a new application and
the [brownfield guide](workflows/brownfield.md) for an existing repository. The
[design-to-implementation guide](workflows/design-to-implementation.md) defines
the handoff between an approved design and code.

## Workflow at a glance

```mermaid
flowchart TD
    I[Intake and priority] --> D[Discovery]
    D --> P[Product requirements]
    P --> G[Product and technical design]
    G --> S{Formal specification needed?}
    S -->|Yes| O[Formal specification]
    S -->|No| W[Reviewed work record]
    O --> W
    W --> B[Branch and implementation]
    B --> T[Tests and required checks]
    T --> R[Review and merge]
    R --> C[Merged-revision CI evidence]
    C --> F[Evidence-gated finish]
    F --> H[Tracker completion and handoff]
```

AI-DLC does not host an autonomous orchestrator. The human and agent decide
what work is useful. Skills provide judgment; the CLI validates, stores, links,
reconciles, and gates the resulting work. MCP exposes shared work, doctor, knowledge and documentation services.

## Stage contracts

| Stage | Purpose | Durable output | Exit condition |
| --- | --- | --- | --- |
| Intake | Reconcile an idea with current priorities | Tracker item or reviewed candidate | The next investigation is explicit |
| Discovery | Establish users, outcomes, constraints, evidence, and unknowns | Bounded problem statement | The problem is clear enough to define or stop |
| Product requirements | Record rationale, scope, outcomes, risks, and acceptance | Reviewed PRD when the change needs one | Material product questions are resolved or named |
| Design | Define journeys, states, system boundaries, interfaces, and consequential choices | Design document, diagram, and linked decisions | Implementers can act without inventing product behavior |
| Specification decision | Decide whether formal behavior needs a specification | Recorded decision and, when required, provider-owned specification | Required scenarios and acceptance criteria are current |
| Work publication | Bind reviewed scope to durable tracker state | `.ai-dlc/work/<id>.toml` and tracker item | The record is reviewed before external mutation |
| Implementation | Deliver the smallest coherent change on the bound branch | Code, tests, migrations, and updated durable docs | Local required checks pass |
| Review and merge | Evaluate correctness, maintainability, risk, and scope | Reviewed pull request and merged revision | Required review, repository rules, and fresh checks pass against the current target branch |
| Verification and finish | Authenticate the merge and its configured evidence | CI receipts and optional deployment evidence | `ai-dlc work finish <work-id>` accepts every configured gate |
| Continuity | Preserve only what the next person or session needs | Handoff, runbook updates, and linked personal notes | Remote state and remaining work are unambiguous |

Each stage consumes reviewed output from the previous stage. Skipping an
artifact is acceptable when the stage explicitly decides it is unnecessary;
silently replacing it with assumptions is not.

## Design to implementation ownership

For both greenfield and brownfield work, skills own discovery, requirements,
design judgment, and the specification decision. The CLI owns reviewed work
records, local checks, machine lifecycle commands, and completion gates. Local
MCP exposes reviewed work operations, read-only doctor inspection, and selected
knowledge operations; machine enrollment mutations are CLI-only in this cycle.
It does not create a second workflow. The design-to-implementation handoff is complete only when the
approved design, any required specification, and the reviewed work record let
implementation proceed without inventing behavior.

## Environment preparation

Use the [machine enrollment runbook](runbooks/machine-enrollment.md) for private
profiles, readiness and client setup. Provider setup belongs in the relevant
runbook: [GitHub](github-ticket-setup.md), [Linear](runbooks/linear-setup.md),
[Plane](runbooks/plane-setup.md), or [Jira](runbooks/jira-cloud-setup.md).
The lifecycle below stays independent of the selected provider.

## Sources of truth

- The repository owns architecture, product rationale, design context,
  decisions, runbooks, code, and tests.
- The configured specification provider exclusively owns formal behavior
  specifications. Repository design documents link to specifications instead
  of copying them.
- The selected delivery tracker owns engineering priority and lifecycle status.
  When an upstream business tracker is used, it owns business priority, outcome
  scope and acceptance; see the Jira/GitHub ownership model below.
- SCM and CI own review, merge identity, and merged-revision evidence.
- Personal knowledge stores continuity, reflection, and private notes. It links
  durable repository material and is not a repository mirror.
- Portable configuration may name required environment variables, such as
  `token_env = "LINEAR_API_KEY"`, but never contains their secret values.
  Machine configuration owns account choices and local paths. `.ai-dlc/local/`
  may hold ignored non-secret control-plane IDs and local metadata. Actual
  credential values stay in an OS keychain, password manager, or secret
  injector and enter only the process environment.

When sources disagree, reconcile their owned facts rather than overwriting one
store with a copy from another.

## GitHub delivery with Jira outcomes

Sean's personal profile selects GitHub Issues for delivery, with a GitHub Project
configured per repository for planning. Jira is the upstream owner of business
outcomes when work needs it. One Jira story or epic can link to several GitHub
delivery issues. Small fixes and maintenance may start in GitHub without a Jira
parent; link them upstream when they affect a business commitment.

This is a manual workflow today. The profile comments express intent, not an
enabled Jira connection or synchronization service. Each work record still has
one selected tracker. Selecting `jira-cloud` instead makes Jira that delivery
tracker; it does not connect Jira outcomes to GitHub issues.

| Location | Owns |
| --- | --- |
| Jira | Business outcome, stakeholder priority, scope and acceptance |
| Repository documents | Discovery, product rationale and design decisions |
| OpenSpec | Required behavioral specifications |
| GitHub Issues | Deliverable engineering tasks, dependencies and acceptance evidence |
| GitHub Projects | Delivery planning, sequencing and progress |
| Pull requests and CI | Review, merge and verification evidence |

### From intake to business acceptance

1. **Intake:** A Jira ticket identifies an outcome. Triage decides whether it
   needs discovery, clarification or delivery planning. Creating the ticket does
   not authorize development. GitHub-originated engineering work enters the same
   shaping and specification decision stages at the depth it needs.
2. **Shaping:** Capture discovery, product requirements when needed, and design
   decisions in repository documents. Review the requirements and record the
   formal specification decision; keep required OpenSpec artifacts current.
3. **Breakdown:** Create reviewed work records for independently deliverable
   GitHub issues. Link their requirements, design and specification, and record
   the Jira outcome URL as `artifacts.jira_parent` when applicable. Sequence the
   issues and their dependencies in GitHub Projects.
4. **Delivery:** Publish and start the reviewed work through AI-DLC, implement
   through pull requests, run required checks, and use `ai-dlc work finish` after
   merge to verify the configured completion gates. A board status alone is not
   delivery evidence.
5. **Acceptance:** When all agreed delivery work is verified, summarize the
   evidence and remaining concerns on Jira as ready for acceptance. Business
   acceptance controls Jira closure. One merged PR or completed child issue does
   not complete the outcome; partial delivery remains visible as outstanding work.

"Ready for acceptance" describes a handoff, not a prescribed Jira status ID or
automatic transition. Use the actual team's reviewed workflow. Jira scope changes
return to shaping and a review of affected specifications and delivery issues.
Cancellation or reopening requires explicit reconciliation of remaining work;
neither system's status automatically propagates to the other.

### Manual links now

Add the parent to the existing artifact table in each applicable work record:

```toml
[artifacts]
# Illustrative URL: replace with the actual Jira outcome's full URL.
jira_parent = "https://example.atlassian.net/browse/TEAM-123"
```

Retain the record's other artifact entries. `jira_parent` is an artifact naming
convention, not a second tracker binding or a validated cross-system parent-child
relationship. New GitHub issue publication includes these artifact references.
Repeat publication preserves authored issue descriptions, so adding the reference
later does not update an already published issue: manually add the link there too.
Maintain reciprocal links and concise delivery summaries on the Jira outcome.
Keep business rationale, design and formal behavior in their owned locations and
link them instead of maintaining competing copies.

Where configured, Atlassian's GitHub integration can show branches, commits and
pull requests on Jira work items when their keys appear in development work.
This provides development visibility; the workflow above still needs its manual
issue links and outcome summaries. See
[Atlassian's GitHub integration guidance](https://support.atlassian.com/jira-cloud-administration/docs/use-the-github-for-jira-app/).

### Gaps before automated synchronization

The existing Jira Cloud adapter supports Jira as the selected tracker. The
following coordination capabilities remain future work:

- Explicit Jira intake that prepares reviewable local discovery and work context.
- Structured outcome-to-delivery mappings across work items and repositories.
- Aggregate reporting of verified, outstanding and blocked delivery work.
- Field ownership and conflict handling: Jira supplies business scope and priority;
  GitHub supplies engineering progress. Changed scope returns for review.
- Retry-safe synchronization that preserves authored content, reconciles uncertain
  writes, and never closes a Jira outcome merely because one PR merged.

Company Jira access and workflow compatibility remain unverified. Manual linking
does not require enabling the Jira adapter; future automation needs the actual
approved company connection and workflow mappings. See
[work-computer setup](workflows/work-computer-setup.md) for GitHub delivery setup
and the explicit Jira-only alternative.

## Capability boundaries

Initialization and adoption may select any subset of `specs`, `tracker`,
`knowledge`, `scm`, `deploy`, and `agent-client`. Selection controls declared
roles and generated provider assets. The runtime retains compatibility
fallbacks for local OpenSpec and GitHub, but a fallback does not choose an
account, repository, or authorization and must not be mistaken for a configured
role. GitHub uses conventional `verify.yml` and `main` defaults unless they are
overridden. The tracker has no fallback.

- Project setup, checks, architecture, design, decisions, and runbooks remain
  useful without external providers.
- The full publish/start/status/finish lifecycle requires configured tracker and
  SCM roles. Without either role, use the local project lifecycle and manual
  tracking, or configure the missing role before publishing work.
- Without a declared specification role, work may deliberately use the local
  OpenSpec compatibility fallback when its formal artifacts exist. Otherwise,
  work that does not require a specification records `requires_spec = false`
  with a reviewed reason; work that does require one configures the role.
- Knowledge, deployment evidence, and agent clients are optional. Their stages
  are omitted when their roles are not selected; deployment becomes a finish
  gate only when configured.
- Omitting SCM also omits the generated GitHub workflow. Local required checks
  still run, but merged-revision CI completion is unavailable.

## Daily operating loop

1. Reconcile tracker priority, work bindings, branch state, and fresh evidence.
2. Use discovery when the problem or outcome is unclear.
3. Draft and review product requirements when durable rationale is needed.
4. Produce the minimum design that closes product and technical ambiguity.
5. Record whether formal specification is required and make it current when it
   is.
6. Review the work record, then publish and start it through AI-DLC.
7. Implement on the bound branch with acceptance and regression tests.
8. Run `ai-dlc project check --required` before review.
9. Immediately before merge, update the branch from the target branch and
   refresh base-bound evidence and checks. Merge through the configured SCM and
   finish through AI-DLC so current specification, merged revision, CI receipts,
   and deployment evidence are checked together.
10. Update durable documentation and leave a concise handoff when continuity is
    needed.

## Completion is evidence-gated

`ai-dlc work finish <work-id>` is the completion boundary for projects with the
required tracker and SCM capabilities. It checks the authenticated merged
revision rather than the local checkout. The generated single-job GitHub
workflow publishes `ai-dlc-receipt`; matrix repositories declare every exact
expected artifact in `scm.receipt_artifacts`. A missing, malformed, dirty,
mismatched, duplicate, or expired receipt blocks completion.

Tracker completion never substitutes for a merge, green CI, a current required
specification, or configured deployment evidence. Failures remain visible and
retryable instead of being converted into success.

## Merge against the current target branch

Documentation-impact dispositions name the exact target-branch commit they were
reviewed against. Pull request CI supplies the pull request's base commit, and
the target-branch run after merge supplies the commit that the merge replaced.
Both runs must see the recorded base, so a merge is safe only when the target
branch has not moved since the evidence was recorded and checked.

Pull request checks do not rerun when the target branch moves, and re-running an
old pull request job reuses its original commit and base. A green check can
therefore describe a superseded base. Immediately before merging:

1. Fetch and update the branch from the target branch.
2. Inspect impact against the new target commit and record dispositions again.
3. Push the update and wait for fresh required checks.
4. Merge only if the target branch is still that commit; otherwise repeat.

Enable the branch protection or ruleset option that requires branches to be up
to date before merging, with the Verify jobs as required checks. The SCM then
enforces this sequence. It is a repository setting that an administrator changes
deliberately; AI-DLC does not change it. `verify.yml` has no merge-queue trigger,
and exact-base evidence cannot anticipate a queued predecessor.

`docs-gate` reports a base mismatch first and names both commits.
`docs-disposition` refuses a base that the checkout does not contain. If a stale
base still reaches the target branch, that merge's run stays failed and
`work finish` stays blocked, because rerunning repeats the same comparison. Do not
edit evidence to name the old base; reconcile the work item explicitly.

## Maintaining this handbook

- Keep lifecycle stages and role names provider-neutral.
- Update [the tool map](workflows/tool-map.md) when a configured provider,
  command, or skill changes.
- Update the greenfield or brownfield guide when initialization or adoption
  behavior changes.
- Update the design handoff when required design evidence changes.
- Store diagrams as Mermaid beside the text they explain. Exported images are
  optional views, never the editable source.
- Change the handbook, project template, relevant skills, and behavior in the
  same pull request when they form one contract.
- Use Git history for evolution; do not maintain a parallel changelog inside
  every guide.
