# AI-DLC roadmap

Updated September 7, 2026 from the current maintainer request, GitHub Project,
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

Claude Code and Codex have implemented adapters. Antigravity needs an explicit
adapter/onboarding child under #19, with current documented paths/transports and
version-specific live qualification. The work computer's OS/architecture and
installed Claude/Antigravity versions must be recorded before claiming that
machine is qualified. Existing Markdown skills alone do not prove client support.

## Current delivery sequence

Independent issues may run in isolated worktrees. Integrate shared interfaces in
dependency order, with TDD, independent review and the required checks.

| Issue | Deliverable | Dependencies / completion boundary |
|---|---|---|
| [#18](https://github.com/Sean-Koval/ai-dlc/issues/18) | GitHub workflow foundation and PR #23 | Completed through AI-DLC finish at merged631d10a with all five receipts |
| [#10](https://github.com/Sean-Koval/ai-dlc/issues/10) | Preserve authored files during workflow-bundle cleanup | Existing isolated implementation; repair remaining successful-cleanup race, then review/integrate/finish |
| [#11](https://github.com/Sean-Koval/ai-dlc/issues/11) | Greenfield/brownfield product shaping | Independent of #10; current PS-01–03 spec, portable skills/templates/examples |
| [#19](https://github.com/Sean-Koval/ai-dlc/issues/19) | Reusable onboarding and native Claude/Antigravity setup | Build on delivered GitHub setup; separate transport/account identity and scoped readiness; explicit Antigravity child |
| [#12](https://github.com/Sean-Koval/ai-dlc/issues/12) | Requirements-to-spec-to-ticket traceability and dependency guards | #11's reviewed artifacts; preserve authored issue content and provider-neutral workflows |
| [#20](https://github.com/Sean-Koval/ai-dlc/issues/20) | Jira Cloud new-work adapter/setup; optional Plane | Common connection contract from #19; actual required fields/transitions; no Jira migration |
| [#14](https://github.com/Sean-Koval/ai-dlc/issues/14) | Portable setup, substitution and fresh-session handoff qualification | #10/#12 and applicable onboarding; distinguish ordinary clone, clean-machine, container and actual client evidence |
| [#13](https://github.com/Sean-Koval/ai-dlc/issues/13) | Optional UI/UX generation/evaluation guidance | #11/#12; UI is optional, not AI-DLC's organizing purpose |
| [#21](https://github.com/Sean-Koval/ai-dlc/issues/21) | Remaining provider substitution/migration qualification | Existing GitHub switch/mappings are delivered; later Plane paths need a real chosen destination |
| [#15](https://github.com/Sean-Koval/ai-dlc/issues/15) | Product-guidance calibration | #11/#12; original cases, fixed experiment protocol, real human ratings and declared budget |
| [#16](https://github.com/Sean-Koval/ai-dlc/issues/16) | Design-guidance calibration | #13; independent evidence and human participation |
| [#17](https://github.com/Sean-Koval/ai-dlc/issues/17) | Retained v4 release obligations | Actual clean/container/cloud evidence, enforced-egress provider conformance, declared evaluations and authorized release publication |
| [#22](https://github.com/Sean-Koval/ai-dlc/issues/22) | Selective Confluence publication | Deferred pending custom server; no vault/site mirroring |

The [current execution plan](superpowers/plans/2026-09-07-work-computer-readiness.md)
coordinates these streams. Issue-specific formal specs remain the behavior
authority. Older implementation plans may supply compatible detail; their obsolete
Linear priority, provider choice, or access-pending claims do not override this
sequence or current GitHub issues. The September 5 roadmap remains in Git history.

## Completion and qualification

Finalize required behavior specifications before review and integration. Use
`ai-dlc work finish` only after its specification, PR and exact merged-CI gates
pass. A Done board option, local check or successful direct adapter call is not
work completion. Parent issues remain open for genuinely undelivered scope.

Prepare missing qualification runners, original cases and runbooks while external
inputs are pending; do not invent machine walkthroughs, human preference, account
permissions or release evidence. The v4 experiment declaration in
`agents/evaluation.toml` has its own model, budget and human-review requirement;
#15/#16 do not silently consume or redefine it.

See [release evidence](release-verification.md),
[GitHub qualification](verification/github-ticket-workflows.md),
[backlog adoption and provenance](planning/github-backlog-migration.md), and
[current executor handoff](handoffs/framework-delivery.md).
