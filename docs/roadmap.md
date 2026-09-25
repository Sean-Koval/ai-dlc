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
for new work, with Plane as an optional alternative; Obsidian remains the private
journal. Delivery runs through reviewed work records, OpenSpec changes, pull
requests and a gated `ai-dlc work finish`. Release publication from a tag is
implemented; the outstanding qualification list is in release verification.

## Next three increments

The September delivery-path, diagnostics and release increments are complete
(#71–#78, #103). The next increments test whether the workflow helps on real work
before adding surface area.

1. **Adoption on real repositories.** Adopt one work repository with Jira Cloud and
   one personal repository with GitHub Issues, deliver ordinary work through them
   for two weeks, and keep a friction log of every refusal, repeated step and
   workaround. The work-repository run supplies the live lifecycle record that
   [#85](https://github.com/Sean-Koval/ai-dlc/issues/85) requires; on success,
   present one qualified work tracker and mark Plane and Linear as available but
   unqualified. Friction-log entries become issues; nothing else enters the queue
   until they are triaged.
2. **A shorter delivery path.** Count the manual commands between a tracker item
   and `work finish` on the adopted repositories, then remove or fold steps until
   the count is halved. The [delivery path baseline](verification/delivery-path-baseline.md)
   records the starting counts and candidate reductions; start with documentation
   evidence that is re-recorded and committed after each non-record edit.
3. **Evaluation that measures value.** The runner, grader, report and
   [baseline specification](../openspec/specs/end-to-end-evaluation/spec.md) from
   [#137](https://github.com/Sean-Koval/ai-dlc/issues/137) are delivered. Their
   deterministic fixture runs verify the machinery, not AI-DLC's value; see the
   [evaluation evidence](verification/end-to-end-evaluation.md). Complete the first
   slice of [#138](https://github.com/Sean-Koval/ai-dlc/issues/138): one real coding
   client, with the same version, model and goal in both arms, taking the same
   seeded task through hidden acceptance tests with AI-DLC and with the bare
   client. Report correctness, turns, time and spend for both. That comparison
   remains pending; use its results to decide the broader client, recovery and
   observer work in #138–#140.

Waiting on environments or decisions, not scheduled:
[#53](https://github.com/Sean-Koval/ai-dlc/issues/53) native client, company and
cross-platform qualification; and the Confluence publication half of
[#50](https://github.com/Sean-Koval/ai-dlc/issues/50)
(`team-document-publication`, no tasks started), which stays deferred under the
"Not planned" entry below until the custom server review happens. The FDE scaffold
half of #50 is delivered.

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

The [September 2026 roadmap ledger](archive/planning/2026-09-roadmap-ledger.md)
preserves the delivered-and-cancelled table and the reconciliation narrative; the
[historical executor handoff](archive/handoffs/framework-delivery.md) preserves the
earlier execution checkpoints.
