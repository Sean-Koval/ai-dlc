# AI-DLC roadmap

The [AI-DLC Project](https://github.com/users/Sean-Koval/projects/2) and
[GitHub issues](https://github.com/Sean-Koval/ai-dlc/issues) own ticket priority
and status. This page states the current outcome and the next increments;
[product direction](product-direction.md) owns the durable product promise, and
[release verification](release-verification.md) owns what a release must prove.

## Current outcome

AI-DLC is usable from a cloned installation on the work computer, with Claude Code,
Codex and Antigravity providing an organized, consistent development workflow. It
prepares tools, integrations, guidance and evidence; the harness performs the work.
Installing the engine from this repository is distinct from adopting a work
repository, which has its own tracker and independent local credentials. Personal
projects use GitHub Issues with repository-associated Projects; work uses Jira Cloud
for new work (Plane is shipped but unsupported, and Linear has been removed);
Obsidian remains the private journal. Hangar intake starts agent jobs from tickets;
AI-DLC keeps its tracker adapters for the local work lifecycle (see the
[tracker boundary](architecture.md#tracker-boundary-with-hangar)). Delivery runs through reviewed work records, OpenSpec changes, pull
requests and a gated `ai-dlc work finish`. Release publication from a tag is
implemented; the outstanding qualification list is in release verification.

Team-flow improvements are tracked in
[#167](https://github.com/Sean-Koval/ai-dlc/issues/167) (guidance for selected
capabilities), [#168](https://github.com/Sean-Koval/ai-dlc/issues/168) (concise team
skill discovery), and [#169](https://github.com/Sean-Koval/ai-dlc/issues/169)
(focused checks and meaningful starter verification). They refine existing setup
and check services; actual time, token savings and failures caught still need
measurement on adopted repositories and in the deferred comparison.

## Next three increments

The September delivery-path, diagnostics and release increments are complete
(#71–#78, #103). The next increments test whether the workflow helps on real work
before adding surface area.

1. **Adoption on real repositories.** Adopt one work repository with Jira Cloud and
   one personal repository with GitHub Issues, deliver ordinary work through them
   for two weeks, and keep a friction log of every refusal, repeated step and
   workaround. The work-repository run supplies the live lifecycle record that
   [#85](https://github.com/Sean-Koval/ai-dlc/issues/85) requires for the local
   lifecycle steps hangar does not perform (`work publish`, a blocked `work finish`
   before merge and a closing `work finish` after merge); on success, present one
   qualified work tracker. Plane already reads as unsupported. Friction-log entries become issues; nothing else enters the queue
   until they are triaged.
2. **A shorter delivery path.** Count the manual commands between a tracker item
   and `work finish` on the adopted repositories, then remove or fold steps until
   the count is halved. The [delivery path baseline](verification/delivery-path-baseline.md)
   records the starting counts, candidate reductions and the delivered per-work,
   content-bound documentation evidence (#146). Re-record only new or stale
   targets; unchanged decisions survive unrelated edits and target-branch movement.
   Use observed adoption friction to prioritize the remaining reductions, including
   the baseline's proposal for one pre-merge command.
3. **Evaluation moves to flightdeck.** The runner, grader, report and skill
   evaluation are frozen (bug fixes only) and handed to
   [flightdeck](https://github.com/Sean-Koval/flightdeck) under ADR 0001; the
   [handoff inventory and port notes](verification/end-to-end-evaluation.md#handoff-to-flightdeck)
   list every moving file. The paired comparison planned in
   [#138](https://github.com/Sean-Koval/ai-dlc/issues/138)–#140 happens in flightdeck,
   and [#195](https://github.com/Sean-Koval/ai-dlc/issues/195) removes the AI-DLC copy
   once flightdeck's ported runner has run.

Waiting on environments or decisions, not scheduled:
[#53](https://github.com/Sean-Koval/ai-dlc/issues/53) native client, company and
cross-platform qualification. The Confluence publication half of
[#50](https://github.com/Sean-Koval/ai-dlc/issues/50) is cut under
[ADR 0001](decisions/0001-refocus-ai-dlc.md); its `team-document-publication` change
(no tasks started) is archived as cancelled, as is `native-harness-verification`
([#175](https://github.com/Sean-Koval/ai-dlc/issues/175)). The FDE scaffold half of
#50 is delivered.

## How status is tracked

- The GitHub Project above holds priority and status; issue closure reasons
  distinguish completed from not-planned scope.
- `ai-dlc context --brief` (MCP `work_context`) lists open work records, the
  required checks and the next command; `ai-dlc work status <id>` reads one record.
- Work completes only through `ai-dlc work finish`, which requires the archived
  specification, the merged pull request and exact merged-revision CI receipts.
  A Done board value, a local check or a direct adapter call is not completion.

## Not planned

Cancelled or deferred scope stays cancelled; nothing here reopens it.

- Qualification of clean machines, hosted clients, live providers and human
  calibration that was closed as not planned (#14, #15, #16, #17, #20, #21).
- Selective Confluence publication (#22), pending review of the custom server.
- Package index publication.

The [September 2026 roadmap ledger](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/planning/2026-09-roadmap-ledger.md)
preserves the delivered-and-cancelled table and the reconciliation narrative; the
[historical executor handoff](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/handoffs/framework-delivery.md) preserves the
earlier execution checkpoints.
