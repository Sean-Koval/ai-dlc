# Consumer onboarding implementation plan

> For agentic workers: use the subagent-driven-development workflow with the bounded task briefs and repository-local ledger.

Implementation authorized by the user on September 26, 2026: “Start implementing these issues one by one.” The existing reviewed CO specification is the contract. This change is independent of #172; native Windows consumer installation remains unqualified on this delivery base. No further design-approval pause is needed for the bounded implementation below.

## 1. Review and contracts
- [x] 1.1 Review CO-01–CO-05, proposed CLI/schema, platform matrix and existing service boundaries with the product/engineering owner; record disposition without treating issue creation as implementation approval.
- [x] 1.2 Identify pure existing resolvers and any needed read-only extraction; confirm enrollment preview is not called for inspection.

## 2. Consumer route and implementation
- [ ] 2.1 Split consumer installation/adoption from contributor setup in canonical entry guidance, including a pre-import native Windows limitation and released/source feature identity.
- [ ] 2.2 Implement the shared read-only preflight and thin CLI interface with explicit target/selection handling, stable findings, exact argument arrays and ordered dependencies.
- [x] 2.3 Compose existing service recommendations without an execute-plan facility, automatic apply, implicit fallback or personal configuration inheritance.

## 3. Acceptance and delivery
- [ ] 3.1 Test fresh/existing projects, missing/conflicting selections, invalid configuration, unknown shell/client, native Windows unsupported routing and preservation/no effects.
- [ ] 3.2 Exercise a disposable supported Unix consumer journey through one target behavior check; record baseline time/manual steps and keep missing native evidence pending under #53.
- [ ] 3.3 Review README, machine enrollment, work-computer setup, tool map, release limits and affected packaged guidance; record content-bound documentation dispositions and update applicable catalog mappings.
- [ ] 3.4 Complete specification/work-record and affected-document review, record required content-bound dispositions, strictly validate this change, run the prepared required checks, and resolve actionable review findings.

## Subsequent delivery gates

After implementation and the checklist above are complete, archive this independently owned change on its bound delivery branch with `ai-dlc work archive`. Repair moved artifact links and any evidence targets actually made stale by archival. Immediately before authorized merge, update from the target branch and refresh required checks/evidence. Finish through `ai-dlc work finish` against the exact merged revision and its configured receipts. These remain mandatory later delivery gates, not checkboxes that must falsely claim post-merge completion before archive. No package publication or paid comparison is authorized by this task list.

## Implementation plan

**Goal:** Return an explicit, read-only consumer setup plan for the selected target, without importing the engine maintainer’s choices.
**Architecture:** A pure application service composes local metadata and existing command recommendations. A thin CLI maps states to exit codes. Existing mutation services retain ownership and execution responsibility.
**Tech stack:** Existing Python, Typer, Pydantic/configuration services and pytest; no new dependency or MCP operation.
**Spec:** `specs/consumer-onboarding/spec.md` and `design.md` in this change.

### Global constraints and review focus

- No subprocess/network/fetch, temporary staging, cache population, configuration writes or credential values during preflight; no apply mode or orchestrator.
- Explicit readable existing target; reject the engine checkout, unknown client and conflicting choices. A new target requires explicit clients; generic is the language-neutral default, with no filename-based Python inference.
- No enrollment inputs means unselected enrollment. Partial source/ref/profile/machine choices are input-required; all required IDs must be supplied, never inferred from the hostname. Do not read or inherit ambient profile values merely because they exist.
- Shell-specific command text is optional derived presentation; `argv` is authoritative. Unknown shell suppresses activation and copyable shell text, with an explicit finding. Native Windows is unsupported on this base; never suggest WSL or translated shell commands.
- A stale generated file is not necessarily an authored ownership conflict. Inspect ownership narrowly and delegate recovery to existing previews.
- Explicit source strings must not leak credentials; report safe identifiers or an input error. Engine version alone does not establish feature parity with historical v0.4.0.
- Existing required checks are recommendations, not observed passes or proof of behavioral quality. A fresh target must add/select its own acceptance check; do not substitute engine contributor checks.

### Task 1: Read-only planning service and acceptance tests

Files: create `src/ai_dlc/setup/onboarding.py`, `tests/test_consumer_onboarding.py`.
Interface: `plan_onboarding(root: Path, *, source: str | None = None, ref: str | None = None, profile_id: str | None = None, machine_id: str | None = None, agent_clients: list[str] | None = None, preset: str | None = None, environ: Mapping[str, str] | None = None) -> dict`. Tests may patch standard platform functions; do not add user-facing simulation flags.
Return the schema-1 target/platform/clients/engine/state/findings/actions/qualification contract in the design. Findings/actions use stable IDs, ordered dependencies, exact existing CLI argv, effects, review requirements and availability. Raise `ValueError` for malformed selection/configuration, return bounded findings for missing observations or unavailable routes. Never execute a recommendation.

- [x] Write failing tests for fresh/adopted target planning, selection conflicts/partial enrollment, unsupported host/client/shell, engine checkout rejection, stale versus edited ownership, safe source metadata and meaningful target-check routing.
- [x] Snapshot target and isolated HOME/XDG/cache/temp state and reject process/network/write entry points while invoking repeated plans; assert identical plans and no effects.
- [x] Implement the smallest service using target-only configuration and pure resolvers. Do not invoke enrollment or adoption previews.
- [x] Run the focused service/readiness/config tests and resolve failures; commit the service with conventional prefix and prepare a review report.

### Task 2: CLI and canonical consumer guidance

Files: modify `src/ai_dlc/cli.py`, create `tests/test_consumer_onboarding_cli.py`; update `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/runbooks/machine-enrollment.md`, `docs/workflows/work-computer-setup.md`, `docs/workflows/tool-map.md`, `docs/release-verification.md`, and relevant `docs/catalog.toml` source mappings. Update generic packaged guidance only where actual instructions require it.
Consumes Task 1’s interface. CLI `project onboard` requires `--root`, offers the documented optional source/ref/profile/machine/client/preset selections and no apply mode. It emits the service JSON and exits 0 only for actionable planning, 1 for blocked/unsupported/input-required, and 2 for invalid arguments/configuration.

- [ ] Add failing CLI tests for required root, no apply option, state/exit mapping, repeated client options and malformed config.
- [ ] Implement the thin command and guide consumers to explicit target installation/adoption/setup/check operations; preserve separate contributor instructions.
- [ ] Name the native Windows installation limitation before CLI import, with #172’s pending support path and no mandatory WSL advice. Historical v0.4.0 does not have this command; use the exact reviewed source executable for the current journey.
- [ ] Run CLI/service and affected guidance checks; commit with a conventional prefix and prepare a review report.

### Task 3: Real consumer evidence and delivery

- [ ] Use a disposable Unix target with isolated personal/XDG state; invoke the actual CLI plan, preview/apply adoption with explicit selections, setup, and a target-owned acceptance command. Observe pass, deliberate behavior failure and restored pass; retain roots, revision, elapsed time/manual command count and limits in existing release verification documentation.
- [ ] Review actual documentation impact, record content-bound dispositions and mapping changes, strictly validate OpenSpec/work records, run required project checks and independent whole-change review.
Delivery requirement: follow the subsequent delivery gates above after implementation verification. Windows/client observations stay unqualified; do not merge or finish #172 as a side effect.
