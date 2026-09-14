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

1. **Delivery path.** Collapse the record-to-PR path so `work start` commits its
   record and `work pr` opens the pull request
   ([#73](https://github.com/Sean-Koval/ai-dlc/issues/73)), create reviewed records
   from tracker items ([#72](https://github.com/Sean-Koval/ai-dlc/issues/72)), and
   archive the OpenSpec change on the delivery branch before merge
   ([#74](https://github.com/Sean-Koval/ai-dlc/issues/74)).
2. **Diagnostics that explain themselves.** Make `project check` find its bootstrap
   runtime and let diagnostics repair the shell entry
   ([#76](https://github.com/Sean-Koval/ai-dlc/issues/76)), replace the JSON context
   brief with a readable "what next" summary
   ([#77](https://github.com/Sean-Koval/ai-dlc/issues/77)), explain binding-drift
   refusals ([#78](https://github.com/Sean-Koval/ai-dlc/issues/78)), and stop
   record-only edits from invalidating documentation evidence
   ([#75](https://github.com/Sean-Koval/ai-dlc/issues/75)).
3. **A published release.** Publish a versioned release with bootstrap artifacts
   and record the `verify-published` outcome
   ([#71](https://github.com/Sean-Koval/ai-dlc/issues/71)).

Repository cleanup after the v0.4.0 audit continues under
[#103](https://github.com/Sean-Koval/ai-dlc/issues/103); the P1 and P2 issues
there and elsewhere follow these three.

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
