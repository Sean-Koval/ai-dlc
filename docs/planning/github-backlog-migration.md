# AI-DLC GitHub backlog adoption

Latest steering: ignore Linear reconciliation for now. The existing GitHub issues
are the work queue. Project-backed GitHub onboarding is the requested default;
see [canonical GitHub Project defaults](../../openspec/specs/github-project-defaults/spec.md).

Updated September 7, 2026. The maintainer authorized moving personal AI-DLC work
to **Sean-Koval/ai-dlc** using the available Linear tickets or latest specifications.
Other personal projects use their own repositories. Jira Cloud is a separate work
setup target; no Jira ticket migration is requested.

## Published and verified

Created 13 open GitHub issues from current repository specifications, acceptance
criteria, execution plans and handoffs. Verified each returned issue identity,
title, full body and open state with a fresh read. Dependencies between newly
created successors are linked in their descriptions. The machine-readable
[mapping](github-backlog-migration.json) preserves original Linear references and
source revisions. This is a reconstructed active/planned backlog, not an import
of comments, attachments, assignees, remote-only tickets or fresh Linear status.

| GitHub issue | Source | Planning status |
| --- | --- | --- |
| [#10: Import pinned workflow guidance and expose it to supported harnesses](https://github.com/Sean-Koval/ai-dlc/issues/10) | SAN-12 | In progress — review blocked |
| [#11: Guide product discovery and feature selection for new and existing products](https://github.com/Sean-Koval/ai-dlc/issues/11) | SAN-13 | Backlog |
| [#12: Carry product requirements into independently deliverable specifications and tickets](https://github.com/Sean-Koval/ai-dlc/issues/12) | SAN-14 | Backlog |
| [#13: Add optional UI/UX design generation and evaluation workflow](https://github.com/Sean-Koval/ai-dlc/issues/13) | SAN-6 | Backlog |
| [#14: Qualify portable setup, provider replacement, and development handoffs](https://github.com/Sean-Koval/ai-dlc/issues/14) | SAN-15 | Backlog |
| [#15: Evaluate product shaping and delivery guidance against baseline behavior](https://github.com/Sean-Koval/ai-dlc/issues/15) | SAN-16 | Backlog |
| [#16: Calibrate UI/UX evaluation and measure its incremental value](https://github.com/Sean-Koval/ai-dlc/issues/16) | SAN-7 | Backlog |
| [#17: Complete remaining portable AI-DLC v4 release verification](https://github.com/Sean-Koval/ai-dlc/issues/17) | Repository spec/plan | In progress — qualification pending |
| [#18: Capability-based GitHub Issues and Projects workflows](https://github.com/Sean-Koval/ai-dlc/issues/18) | Repository spec/plan | In progress — qualification pending |
| [#19: Complete reusable provider onboarding and native MCP setup](https://github.com/Sean-Koval/ai-dlc/issues/19) | Repository spec/plan | In progress — Project-default child reviewed |
| [#20: Add optional Plane and Jira Cloud lifecycle adapters](https://github.com/Sean-Koval/ai-dlc/issues/20) | Repository spec/plan | Proposed — remaining parent scope |
| [#21: Qualify remaining tracker substitution and migration paths](https://github.com/Sean-Koval/ai-dlc/issues/21) | Repository spec/plan | Proposed — remaining parent scope |
| [#22: Evaluate selective Confluence publication through existing tools](https://github.com/Sean-Koval/ai-dlc/issues/22) | Repository spec/plan | Deferred |

SAN-9, SAN-10 and SAN-11 have archived/canonical specifications; they were not
reopened as active successors. Integrated planning and profile enrollment also
remain historical. SAN-12 was read from its separate branch at `04c65cb`: the
accepted failed-stage retention fix does not resolve the separate successful
backup cleanup race. Its successor is still open with that limitation.

## Project created and verified

The [AI-DLC Project](https://github.com/users/Sean-Koval/projects/2) now contains
all 13 issues. The official GitHub MCP server verified the signed-in owner as
Sean-Koval, discovered no existing Project, created Project #2, attached the
issues, and read back their actual Status values. Views are **All work** (table)
and **Delivery board** (board). Issues #10, #17, #18 and #19 are In Progress;
the other nine are Todo. Proposed/deferred distinctions remain in issue bodies
and the inventory above; all issues remain open. The mapping records the actual
Project identity and discovered field/option IDs.

Repository association is verified independently of issue membership: after the
AI-DLC setup apply, `repository.projectsV2` returned this exact Project ID under
`Sean-Koval/ai-dlc`, with no remaining result page.

## Activated GitHub setup and local work

The GitHub CLI permission refresh completed as Sean-Koval. AI-DLC's default
connection inferred the repository, selected the existing AI-DLC Project, linked
it to the repository, and saved its actual account/Project/field/option identities.
The official MCP connection remains available separately; no credentials are tracked.

The reviewed default-only plan changed only `roles.tracker` to `github-issues`.
The subsequent selected plan freshly verified and mapped eight work records to
issues #11–#18. This explicitly enrolled the previously tracker-unbound GitHub
workflow record into #18. Non-tracker values and effective identities were
preserved; the v4 record's previously implicit fingerprints were materialized.
All unselected work files remained byte-identical. Generated project guidance
now selects GitHub Issues.

Durable migration evidence:
- [Default switch](../../.ai-dlc/migrations/3c6091dde4bf4c92929acec3f64b7340.json).
- [Eight selected mappings](../../.ai-dlc/migrations/183724c897f44ca5b445ccf2a9893273.json).

These changes are on `codex/github-ticket-workflows`, pending integration through
PR #23. The separate active SAN-12 checkout and its retained mapping remain
unchanged; its GitHub successor #10 is already on the board. Parent planning
issues #19–#22 do not yet have local execution bindings. Historical Linear aliases
and references are retained; no Linear calls or remote changes were needed.

## Live workflow qualification

[Disposable issue #24](https://github.com/Sean-Koval/ai-dlc/issues/24) exercised the
production adapter and work service with the actual repository and Project.
Publish retained its issue reference after a real uncertain attachment response;
retry recovered membership without creating another issue. A deliberately lost
reply after a successful live start exercised journal recovery. Retried start
verified In Progress while the native issue remained open. The real unmerged PR
blocked work finish and left the issue open.

Direct adapter checks on this test issue then verified close, reopen, close and
closed-state reconciliation. Those are adapter conformance checks, not a gated
work-finish success. Cleanup closed the test issue and removed only its Project
item; all 13 backlog issues remain open on the board. The captured local evidence
is `.ai-dlc/local/github-live-qualification.json`. The initial attachment mismatch
was transient; its exact remote cause is unproven. Recovery was observed live,
not inferred from mocked responses. New-Project creation through AI-DLC remains
fixture-qualified; creation of the real board used official MCP.

## Framework follow-through

Track remaining onboarding under [#19](https://github.com/Sean-Koval/ai-dlc/issues/19):
infer the project repository, discover Projects by name, inspect operation-level
permissions, reuse native MCP/OAuth where supported, and explain any separate
lifecycle authentication requirement. Successful account/profile reads alone
must not imply issue writes or Projects access. Use the existing extension and
capability contracts; do not add vendor branches throughout workflow services.

Plane remains optional; Jira is onboarding/new-work support only under
[#20](https://github.com/Sean-Koval/ai-dlc/issues/20). Confluence remains deferred
under [#22](https://github.com/Sean-Koval/ai-dlc/issues/22), preserving private
Obsidian notes and selective shared publication. Parent issues describe remaining
scope so the implemented GitHub child is not duplicated.

Live evidence now includes issue/MCP Project operations, AI-DLC existing-Project
setup, workflow/adapter mutation and recovery, and verified local migration.
It does not establish a successful gated work finish or merged-revision CI.
[Draft PR #23](https://github.com/Sean-Koval/ai-dlc/pull/23) carries the implementation
and activation changes. The earlier candidate passed all five platform jobs;
activation-revision checks are recorded in the verification record. No Linear
closure/deletion, Jira mutation, document publication, spec archive, merge or
work finish completion occurred.
