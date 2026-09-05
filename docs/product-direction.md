# AI-DLC product direction

Status: approved direction from the maintainer's September 5, 2026 review and
documentation/delivery request. Roadmap capabilities are planned work, not claims
that they already ship.

## Product promise

AI-DLC prepares a development environment, connects the user's preferred tools,
and equips the chosen harness with a consistent way to take a new product or an
existing product through a verified improvement.

Its durable value is the relationship between tools, artifacts, decisions, and
workflows. OpenSpec currently provides formal specification, Linear provides
tracking, and Codex/Claude Code are the implemented client adapters. Those choices
are replaceable. Stable responsibilities survive provider changes.

The harness performs development and can use installed tools directly. AI-DLC
provides setup, guidance, integration, validation, and evidence services where
useful. Existing project policies still determine required checks and completion.

## User outcomes

1. Enroll another supported machine/environment and recover the same selected
   tools and guidance with independent local credentials, paths, and accounts.
2. Open a new or existing repository and let the harness discover selected
   providers, installed tools, authoritative instructions, artifacts, and next action.
3. Shape a vague idea or observed problem into a worthwhile bounded increment,
   with evidence, assumptions, alternatives, and explicit success criteria.
4. Translate outcomes into behavioral specifications, deliverable tickets, and
   verification without repeatedly copying the same information.
5. Add or replace components with clear compatibility, ownership, and update rules.
6. Evaluate delivered products and the guidance used to produce them.

## Responsibilities and replaceability

| Part | Stable responsibility | Current foundation | Next delivery |
| --- | --- | --- | --- |
| Environment | Reproduce tools and local bindings | Bootstrap, enrollment, native recipes, project setup | Connect roles to required modules and readiness |
| Integrations | Connect capabilities to selected systems | Provider registry, contracts, configuration | Component metadata and scoped onboarding |
| Harness support | Expose tools, guidance, and context | Managed Codex/Claude assets and optional MCP definitions | Provider guidance index and pinned Markdown bundles |
| Workflows | Guide decisions and handoffs | Discovery/PRD/spec skills and project guides | Worked product-shaping and delivery-slice workflows |
| Evaluation | Establish achieved outcomes | Checks, gates, pending skill experiments | Target walkthroughs and product/design comparisons |

## Product development workflow

Greenfield starts with audience, problem, evidence, alternatives, and the smallest
useful outcome. Brownfield starts with observed behavior, users, integrations,
compatibility constraints, and an incremental change. Both converge on a shaped
outcome, requirements, applicable design, behavioral specification, delivery
slices, implementation, and verification. Findings can send work back to discovery.

Product requirements explain intent and scope. Specifications define observable
behavior. Tickets organize deliverable slices, dependencies, and status. Tasks
describe implementation steps. Links and stable IDs preserve these relationships.

UI/UX is one optional workflow in this sequence. Its generation/evaluation loop
serves changes requiring interaction or visual judgment. Other work uses suitable
methods: compatibility tests, architecture review, migration rehearsals, API
contracts, or operational evidence. Small work uses small artifacts.

## Principles and limits

- Prefer existing tools; build integration where it removes coordination work.
  Prove a small component contract with real adapters before expanding it.
- Make installation, configuration, instructions, and readiness understandable
  together while preserving their separate data ownership.
- Carry portable state through versioned repositories; keep secrets and machine
  bindings local. Never infer an account from an unrelated session.
- Preserve authored content, active bindings, and existing contracts on updates.
- Make product choices explicit before coding; an executor must not invent scope,
  approval, evidence, or a missing cross-ticket interface.
- Measure observed outcomes. Green tests alone do not prove product value, user
  preference, or successful live platform qualification.
- Consistency means the same intended workflow with honest capability differences,
  not an assertion that every environment supports every tool.

## Delivery boundaries

Initial qualification targets: native macOS arm64 and an Ubuntu 24.04 arm64
devcontainer. Each remains unverified until its actual walkthrough succeeds.
Hosted platforms, extra harness adapters, executable workflow packages, knowledge
onboarding, and release publication remain separately scoped follow-ons.

The code remains a v4 implementation candidate. Original v4 release tasks remain
open where evidence is missing; this roadmap does not relabel that work.

## Navigation

- [Roadmap](roadmap.md)
- [Delivery architecture](design/framework-delivery.md)
- [Executor handoff](handoffs/framework-delivery.md)
- [V4 proposal](../openspec/changes/portable-development-v4/proposal.md)
- [Enrollment design and follow-on cycles](superpowers/specs/2026-09-03-portable-profile-enrollment-design.md)
- [Current architecture](architecture.md)
- [Actual release evidence](release-verification.md)
