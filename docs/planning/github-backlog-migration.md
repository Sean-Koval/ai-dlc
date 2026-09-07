# AI-DLC GitHub backlog adoption

Latest steering: ignore Linear reconciliation for now. The existing GitHub issues
are the work queue. Project-backed GitHub onboarding is the requested default;
see `openspec/changes/github-project-defaults`.

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

Repository association is a separate operation from issue membership. Linking
this Project into the repository's Projects tab remains pending the GitHub CLI
Project permission upgrade. Do not claim that association from the 13 attached
items alone.

## Access and remaining local setup

The connected GitHub app's issue-create request returned HTTP 403; existing
GitHub CLI authentication created and verified the issues instead. The official
GitHub MCP server v1.12.0 completed browser OAuth and performed the live Project
operations above. Its binary archive checksum was verified. The machine-local
server enables only account and Projects tools; credentials are not tracked.

AI-DLC's lifecycle adapter currently uses GitHub CLI authentication separately
from harness MCP authentication. The CLI credential lacked Project permission;
a local permission refresh is awaiting the maintainer's browser authorization.
Browser automation is unavailable, and the authorization page must be completed
directly by the maintainer. No token should be copied into chat or configuration.

After that authorization, run the new default connection preview and inspect
its exact existing Project selection, then apply it to verify/link the repository
and configure the alias. The local target mapping is
`.ai-dlc/local/github-backlog-mappings.toml`; it is not an applied migration.
Existing tracker aliases, default role and retained work records remain unchanged.
Do not hand-edit bindings to bypass verification. Coordinate any SAN-12 binding
change with its separate checkout rather than overwriting its in-progress work.
Linear reconciliation is explicitly deferred and is not a prerequisite to
organizing or implementing the GitHub backlog.

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

This operation establishes live issue creation/read evidence through GitHub CLI
and Project creation, membership, status and view updates through official MCP.
It does not qualify AI-DLC adapter transitions, recovery, migration application,
completion gates, merged CI or release platforms. No Linear closure/deletion,
Jira mutation, document publication, spec archive, merge or finish occurred.
Implementation is now published in [draft PR #23](https://github.com/Sean-Koval/ai-dlc/pull/23);
its CI and remaining live adoption gates are pending.
