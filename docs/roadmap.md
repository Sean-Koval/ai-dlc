# AI-DLC roadmap

Reconciled September 10, 2026 from the current maintainer request, GitHub Project,
formal specifications and implementation evidence. The
[AI-DLC Project](https://github.com/users/Sean-Koval/projects/2) owns current ticket
priority/status. This document owns delivery dependencies and the immediate
outcome; [product direction](product-direction.md) owns the durable product promise.

## Current outcome

Make AI-DLC usable from a cloned installation on the work computer, with Claude
and Antigravity providing an organized, consistent development workflow. AI-DLC
prepares tools, integrations, guidance and evidence; the harness performs the work.
Installing the engine from this repository is distinct from adopting a work
repository, which has its own tracker/project and independent local credentials.
Do not reuse AI-DLC's personal GitHub Project/account binding as work configuration.

Personal projects use GitHub Issues with repository-associated Projects by default.
Work uses Jira Cloud for new work; no Jira migration is requested. Plane is an
optional alternative. Obsidian remains the private journal and knowledge base.
Selective Confluence publication is deferred until the custom MCP server can be
inspected; it does not block the development workflow.

## Verified foundation and immediate gaps

Implemented foundations include source bootstrap, profile enrollment, scoped
configuration, provider contracts, managed assets, readiness, work records and
completion gates. Provider metadata, connected readiness and Linear onboarding
have archived specifications. GitHub Issues/Projects setup, workflow operations
and eight selected local mappings are implemented in PR #23. The Project is
linked to `Sean-Koval/ai-dlc`; authorization and activation are complete.

Clean candidate `29b67b3` passed all required checks with 1,138 tests. Candidate
`332f5b0` passed all five platform CI jobs. Live GitHub setup, bounded lifecycle
recovery and local migration have separate evidence. PR #23 is now merged at `631d10a`; all five exact merged-revision receipts
passed, and AI-DLC work finish completed #18 (native completed and Project Done).

PR [#25](https://github.com/Sean-Koval/ai-dlc/pull/25) delivered portable bundles,
product shaping, native Claude Code/Codex/Antigravity project adapters and the
shared provider connection service at merged `ab6b774`. All five platform receipts
passed for that revision. Fresh-clone source bootstrap and gated finish completed
#10 and #11; both native issue state and Project status confirm completion.

PR [#26](https://github.com/Sean-Koval/ai-dlc/pull/26) delivered reviewed traceability,
toolset selection, native connection composition, Jira and optional Plane new-work
onboarding, Design PM guidance and setup reliability. The
[integration record](verification/work-computer-toolsets.md) records exact tested
revisions and review findings. PR26 merged at `189913b`; all five exact
merged-revision checks passed. Gated finish completed #12, #13 and #19, each
confirmed Completed and Project Done. Native client recognition,
authentication and version-specific live qualification remain separate from file
rendering. Record the work computer's OS/architecture and installed Claude and
Antigravity versions before qualifying that machine.

## Delivery status at plan approval

GitHub native closure reasons were checked for this reconciliation. Issues #10,
#11, #12, #13, #18 and #19 are Completed. Issues #14, #15, #16, #17, #20, #21
and #22 are CLOSED with reason NOT_PLANNED: cancelled, not delivered. The board's
Done value does not change that meaning. There were no open issues at approval;
new documentation work is tracked separately and does not reopen cancelled scope.

PR [#28](https://github.com/Sean-Koval/ai-dlc/pull/28) merged at
`74b90c67f9f0b29a0a4bae688ea6b670608aea18`. Five CI checks passed on its head
`6c0a732`; this is head evidence, not a claim of exact merged-revision receipts
or gated work finish. It delivered optional documentation navigation, local portals
and read-only catalog checks. See the [DK-01–07 reconciliation](verification/project-knowledge-repair.md)
and [documentation baseline](verification/documentation-baseline.json).

The next approved increment, [issue #29](https://github.com/Sean-Koval/ai-dlc/issues/29),
reconciles documentation authority and lifecycle.
Proposed follow-ons cover document evidence review, Obsidian project workspaces,
company guidance bundles, documentation impact and workflow qualification; their
OpenSpec changes and newly published issues own scope and priority.

## Delivered and cancelled scope

This table records delivery and cancellation; it is not a queue to execute.

| Issue | Deliverable | Dependencies / completion boundary |
|---|---|---|
| [#18](https://github.com/Sean-Koval/ai-dlc/issues/18) | GitHub workflow foundation and PR #23 | Completed through AI-DLC finish at merged631d10a with all five receipts |
| [#10](https://github.com/Sean-Koval/ai-dlc/issues/10) | Preserve authored files during workflow-bundle cleanup | Completed through AI-DLC finish at merged ab6b774 with five receipts; issue Completed and Project Done |
| [#11](https://github.com/Sean-Koval/ai-dlc/issues/11) | Greenfield/brownfield product shaping | Completed through AI-DLC finish at merged ab6b774 with five receipts; issue Completed and Project Done |
| [#19](https://github.com/Sean-Koval/ai-dlc/issues/19) | Reusable onboarding and native Claude/Antigravity setup | Completed through gated finish at merged189913b with five receipts |
| [#12](https://github.com/Sean-Koval/ai-dlc/issues/12) | Requirements-to-spec-to-ticket traceability and dependency guards | Completed through gated finish at merged189913b with five receipts |
| [#20](https://github.com/Sean-Koval/ai-dlc/issues/20) | Jira Cloud new-work adapter/setup; optional Plane | Cancelled (CLOSED / NOT_PLANNED); Jira/Plane adapters shipped; actual selected deployment qualification remains unverified |
| [#14](https://github.com/Sean-Koval/ai-dlc/issues/14) | Portable setup, substitution and fresh-session handoff qualification | Cancelled (CLOSED / NOT_PLANNED); Some bootstrap/continuity evidence exists; full clean-machine and client qualification remains unverified |
| [#13](https://github.com/Sean-Koval/ai-dlc/issues/13) | Optional UI/UX generation/evaluation guidance | Completed through gated finish at merged189913b with five receipts; UI remains optional |
| [#21](https://github.com/Sean-Koval/ai-dlc/issues/21) | Remaining provider substitution/migration qualification | Cancelled (CLOSED / NOT_PLANNED); GitHub mappings shipped; actual Plane substitution remains unqualified |
| [#15](https://github.com/Sean-Koval/ai-dlc/issues/15) | Product-guidance calibration | Cancelled (CLOSED / NOT_PLANNED); Prepared cases/protocol are not human evaluation results |
| [#16](https://github.com/Sean-Koval/ai-dlc/issues/16) | Design-guidance calibration | Cancelled (CLOSED / NOT_PLANNED); Prepared stimuli/protocol are not matched model runs or human ratings |
| [#17](https://github.com/Sean-Koval/ai-dlc/issues/17) | Retained v4 release obligations | Cancelled (CLOSED / NOT_PLANNED); Full platform/provider/evaluation evidence and release publication remain outstanding |
| [#22](https://github.com/Sean-Koval/ai-dlc/issues/22) | Selective Confluence publication | Cancelled (CLOSED / NOT_PLANNED); Selective Confluence publication remains unimplemented pending custom server review |

The [historical execution plan](archive/planning/2026-09-07-work-computer-readiness.md)
records the earlier work-computer sequence; it is not an active backlog. Issue-specific formal specs remain the behavior
authority. Older implementation plans may supply compatible detail; their obsolete
Linear priority, provider choice, or access-pending claims do not override this
status record or current GitHub issues. The September 5 roadmap remains in Git history.

## Completion and qualification

Finalize required behavior specifications before review and integration. Use
`ai-dlc work finish` only after its specification, PR and exact merged-CI gates
pass. A Done board option, local check or successful direct adapter call is not
work completion. Cancelled issues do not prove delivery of their undelivered scope.

For separately approved qualification work, prepare runners, original cases and
runbooks while external inputs are pending; do not invent machine walkthroughs, human preference, account
permissions or release evidence. The v4 experiment declaration in
`agents/evaluation.toml` has its own model, budget and human-review requirement;
#15/#16 do not silently consume or redefine it.

See [release evidence](release-verification.md),
[GitHub qualification](verification/github-ticket-workflows.md),
[backlog adoption and provenance](archive/planning/github-backlog-migration.md), and
[current executor handoff](handoffs/framework-delivery.md).
