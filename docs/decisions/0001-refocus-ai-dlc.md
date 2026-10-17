# Decision: refocus AI-DLC on workflow, machines and work lifecycle

Status: accepted
Owner: Sean Koval
Date: 2026-10

## Context

AI-DLC grew to about 28,000 lines of Python in `src/ai_dlc/`, 46 OpenSpec
capability specifications and several megabytes of documentation. Its product
promise read as a harness definer and evaluator: it rendered guidance for every
runtime, ran skill evaluations and described hosted follow-ons.

Three neighbouring tools now own those jobs more directly. Hangar runs coding
agents in cloud sandboxes and renders their configuration at claim time.
Flightdeck judges harness changes with paired experiments over recorded runs.
The governed workspace owns policy decisions, approvals and receipts. Keeping
parallel versions of those responsibilities in AI-DLC adds maintenance without
adding evidence. The planning record is the
[2026-10 harness plan](https://claude.ai/code/artifact/ddea4e99-7068-4c36-8bac-d9cda53c0f4c).

## Options considered

1. Keep growing AI-DLC as the harness compiler and evaluator. Rejected: hangar's
   claim-time renderer is what actually runs in sandboxes, and evaluation needs
   run data that only the sandbox fleet produces.
2. Retire AI-DLC. Rejected: developers still need a reproducible machine, a
   repository-owned workflow and a CI-receipt-gated finish.
3. Freeze AI-DLC to three jobs and move or cut the rest. Accepted.

## Decision

AI-DLC is a local workflow, machine-provisioning and work-lifecycle tool. It does
three jobs:

1. **Workflow plugin author.** It authors one optional workflow plugin
   (guidance, hooks and team skills) that a team harness can pin and switch on or
   off, and it renders managed sections into developer repositories.
2. **Developer-machine provisioner.** It enrolls, bootstraps and provisions
   developer machines from versioned profiles.
3. **CI-receipt-gated work lifecycle.** It binds reviewed work to a tracker item,
   branch and pull request and finishes it only against the merged revision and
   its CI receipts.

New features, documentation growth and new OpenSpec capabilities outside the
in-scope list below stop. Changes outside the list are closed with a pointer to
this decision; bug fixes in frozen areas are welcome.

### What moved where

| Responsibility | New owner |
| --- | --- |
| Harness and skill evaluation (`ai-dlc eval`) | Flightdeck |
| Per-runtime rendering for sandboxed agents | Hangar claim-time renderer |
| Tracker intake for agent jobs | Hangar |
| Policy decisions, approvals and governance | Governed workspace |

### In-scope list

*Active*:

- Work lifecycle: `work new/start/pr/archive/finish`, the finish gates
  `specification-current`, `pr-merged` and `ci-green`, and CI receipts.
- Machine enrollment, bootstrap and provisioning, including finishing native
  Windows ([#172](https://github.com/Sean-Koval/ai-dlc/issues/172)).
- Ownership-digest managed sections (`harness/agents.py`,
  `.ai-dlc/agent-ownership.json`).
- `SCOPES` layering (`config.py`).
- The skills lockfile (`agents/skills.lock.json`).
- The workflow plugin ([#191](https://github.com/Sean-Koval/ai-dlc/issues/191)
  to [#193](https://github.com/Sean-Koval/ai-dlc/issues/193)).
- Local MCP (`ai-dlc mcp serve`).
- The documentation gate.
- The local knowledge provider (Obsidian vault).

*Frozen, bug fixes only*:

- FDE scaffold (`ai-dlc fde`).
- Design capture and frontend packs.
- Team sources and teamai import.
- Effective-environment reports.
- The documentation subsystem (`ai-dlc docs ...`).
- GitHub Issues/Projects and Jira Cloud adapters.

*Moving out*:

- `ai-dlc eval` and skill evaluation, to flightdeck
  ([#194](https://github.com/Sean-Koval/ai-dlc/issues/194)).
- Per-runtime rendering growth, to hangar
  ([#196](https://github.com/Sean-Koval/ai-dlc/issues/196)). No new clients, client
  formats or per-runtime translation in AI-DLC's renderer; cloud sandboxes are
  rendered by hangar at claim time. The `devcontainer`, `codex-cloud` and
  `claude-cloud` execution targets are removed.

*Cut*:

- Linear ([#199](https://github.com/Sean-Koval/ai-dlc/issues/199)).
- Legacy `scaffold` ([#201](https://github.com/Sean-Koval/ai-dlc/issues/201)).
- Confluence publication ([#50](https://github.com/Sean-Koval/ai-dlc/issues/50)).
- Native harness verification ([#175](https://github.com/Sean-Koval/ai-dlc/issues/175)).

## Consequences

- AI-DLC no longer claims to evaluate harnesses or to define what runs in cloud
  sandboxes. The workflow plugin is one optional component that hangar and
  flightdeck can carry and compare; AI-DLC does not decide whether it is enabled.
- Issues outside the in-scope list receive the `scope:frozen` label and a pointer
  here. Bug reports in frozen areas stay open.
- Code moves and deletions happen in their own issues; this decision does not
  move code. Moved and cut areas keep working until those issues land.
- A later decision may reopen a frozen area. Until then, this list is the scope
  boundary for contributors and agents.

## Links

- [Product direction](../product-direction.md)
- [Roadmap](../roadmap.md)
- [Repository guidance](https://github.com/Sean-Koval/ai-dlc/blob/main/AGENTS.md)
- [Contributing](https://github.com/Sean-Koval/ai-dlc/blob/main/CONTRIBUTING.md)
