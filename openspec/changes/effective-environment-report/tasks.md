# Effective environment report implementation plan

> Execute with subagent-driven-development; keep briefs, reports and the ledger in ignored `.ai-dlc/local/effective-environment-report/`.

The user authorized implementing the issues sequentially, including push and merge.
This change starts from #173's completed merge. The reviewed disposition in
`design.md` resolves implementation details; EER-01–EER-05 remain the contract.

## 1. Contract review
- [x] 1.1 Review EER-01–EER-05, schema/CLI compatibility, desired-field allowlist, completeness semantics and drift classes; record product/engineering disposition.
- [x] 1.2 Map pure local collectors from status/readiness/workspace diagnostics and version/provenance adapters; enumerate unsupported provenance rather than infer it.

## 2. Reporting and comparison
- [ ] 2.1 Implement schema validation, positive privacy projection, explicitly opt-in bounded local version probes and stable configuration/observation identity calculation in the existing environment service.
- [ ] 2.2 Add opt-in status export and offline doctor modes, preserving default contracts and safe output publication.
- [ ] 2.3 Implement offline two-file comparison with deterministic findings, scoped next actions and exact error/exit semantics.

## 3. Verification and handoff
- [ ] 3.1 Cover equal/different source at 0.4.0, dirty/unknown provenance, partial state, drift classes, expected platform differences, invalid/oversized payloads and probe limits.
- [ ] 3.2 Verify no leaks using sentinel secrets/private paths in every input and error channel, including digest inputs; prove no provider probes, remote fetches or native sessions run.
- [ ] 3.3 Verify repeated export identity stability and native-evidence invalidation boundary; document missing real cross-machine evidence under #53 without claiming fixture qualification.
- [ ] 3.4 Review machine enrollment, architecture, tool map, work-computer setup and release verification; record content-bound dispositions and applicable catalog mapping updates.
- [ ] 3.5 Complete specification/work-record and affected-document review, record required content-bound dispositions, strictly validate this change, run the prepared required checks, and resolve actionable review findings.

## Subsequent delivery gates

After implementation and the checklist above are complete, archive this independently owned change on its bound delivery branch with `ai-dlc work archive`. Repair moved artifact links and any evidence targets actually made stale by archival. Immediately before authorized merge, update from the target branch and refresh required checks/evidence. Finish through `ai-dlc work finish` against the exact merged revision and its configured receipts. These remain mandatory later delivery gates, not checkboxes that must falsely claim post-merge completion before archive. No package publication or paid comparison is authorized by this task list.

## Implementation tasks

**Goal:** Give teams useful, safe comparisons without claiming unknown environments match.
**Architecture:** Closed schema and pure identity/comparison functions; independent local collection and optional bounded version probes; thin compatible CLI and narrow file publication. No new dependency or provider/probe framework.
**Specification:** `specs/effective-environment-report/spec.md` and reviewed `design.md`.

### Task 1: Strict schema, identities and pure comparison

Own `src/ai_dlc/environment/report_schema.py`, `src/ai_dlc/environment/report_compare.py`, and corresponding focused tests. Follow the reviewed design's exact record fields, limits and privacy boundaries. Use existing Pydantic strict validation if helpful; do not add dependencies or a configurable schema engine.

Public interfaces: `finalize_report(payload: dict) -> dict` validates the safe payload and calculates the three digests; `parse_report(raw: bytes) -> dict` enforces byte/depth/JSON/schema/identity limits; `report_bytes(report: dict) -> bytes` returns validated canonical UTF-8 JSON; `completeness(report: dict) -> tuple[bool, bool]` derives configuration and observation coverage. `compare_reports(left: dict, right: dict) -> dict` validates both, produces deterministic safe findings and completeness booleans; `comparison_exit_code(result: dict) -> int` maps blocking/incomplete to 1, otherwise 0. Validation errors use bounded fixed text, never Pydantic raw input diagnostics. The collector will supply the declared record shape and use finalize_report; it must not need to fabricate known provenance. Document closed reason/state/action constants in the module, keeping vocabularies no larger than required scenarios.

- [ ] Write failing fixtures for complete comparison, missing/dirty/equal-version-different-source identity, profile/source/guidance drift, supported/unknown/unsupported platform differences, exact/range runtime constraints, client editions, optional unknowns and auth differences.
- [ ] Implement the closed schema and pure functions; test duplicate keys/IDs, bool-as-int, unknown fields, invalid versions, oversized/deep inputs, forged/inconsistent identities and safe bounded errors.
- [ ] Prove identity stability across time/auth/native evidence, configuration changes and observed version changes. Verify private excluded fields are rejected before digest calculation; incomplete matching values never imply parity.
- [ ] Run task-focused tests plus format/lint/types; self-review and commit. Record interfaces, reason vocabularies, red/green evidence and concerns in the task report.

### Task 2: Read-only local collection and explicit version probes

Own `src/ai_dlc/environment/report.py`, `src/ai_dlc/environment/version_probes.py` and focused tests. Consume Task 1's record contract; do not change it without recording the reason and notifying the controller. Public interface `collect_report(root: Path, *, home: Path | None = None, environ: Mapping[str, str] | None = None, probe_versions: bool = False) -> dict`. Reuse pure/local configuration, enrollment and component readers, never compound doctor/workspace/machine-plan/render entry points. No provider Registry, subprocess, network, cache mutation, personal client scan or credential export by default. Independent scope failures retain independent observations and mark effective resolution incomplete.

Version probes are fixed built-in executable/argument/parser operations with five-second timeout, actual combined 16 KiB capture bound and minimal environment; no shell/configured command execution. Trusted provenance is absent in current source/release installations and stays unknown. Existing raw lock/ownership hashes cannot be exported as safe content identity. Project/client selections, desired pins, declared native aliases and credential-presence booleans use a positive projection; no private path or secret enters output or digest inputs. Do not infer platform/edition compatibility from installation recipes/hook fixtures. For guidance, use only a narrowly justified safe projection when desired owned content can actually be inspected without effects; otherwise honest nulls and observed missing/conflict states.

- [ ] Write failing isolated-home fixtures with secret sentinels in profile URLs, commands, env values, machine paths, client files and raised errors. Block process/network/write entry points in default mode and prove snapshots unchanged.
- [ ] Implement independent local collection, module/runtime selection and narrow guidance observation. Malformed state produces safe scoped unknowns rather than personal defaults or wholesale failure.
- [ ] Exercise actual optional subprocess timeout/output caps, missing tools, strict version parsing and discarded secret output/errors; do not run a real provider/native model session.
- [ ] Run affected collector/schema/comparison tests and format/lint/types; self-review, commit, and report actual evidence/limits.

### Task 3: Safe report files and compatible CLI options

Own thin additions to `src/ai_dlc/cli.py`, `src/ai_dlc/environment/report_io.py`, a minimal shared filesystem change only if required, and focused file/CLI tests. Consume the preceding interfaces. Preserve no-option machine status and ordinary doctor behavior byte/semantic contracts. Status export requires an explicit root; `--export -` outputs JSON. Compare takes exactly two files and never constructs a manager or collector. Both doctor CLI surfaces use the same report service for the opt-in mode. Reject incompatible option combinations and probe-only use before any effects. MCP remains unchanged.

Validate serialization completely before exclusive atomic private publication, refusing any existing file/link or unsafe ancestor. Use bounded no-follow two-file reads and safe fixed errors. Keep root/destination values and raw exceptions out of diagnostics. Do not introduce a general filesystem abstraction or weaken existing callers' ownership/recovery semantics.

- [ ] Write failing compatibility, exact 0/1/2 exit, mutually exclusive options, stdout export and invalid-input no-output tests. Include colored CLI errors to avoid presentation-dependent assertions.
- [ ] Implement thin selection and file boundaries; verify compare performs no local environment inspection and offline doctor performs no health checks.
- [ ] Test existing destination preservation, symlink/ancestor substitution refusal, bounded reads, private atomic publication and failure cleanup with appropriate platform-scoped cases.
- [ ] Run affected default/new CLI and filesystem tests plus format/lint/types, then self-review, commit and report.

### Task 4: Documentation, fixture evidence and delivery

Update existing machine-enrollment runbook, architecture, tool map, work-computer setup, release verification and their catalog mappings. Explain unknowns, unsigned reports, default no-probe behavior, explicit executable trust, scoped identities and unchanged doctor defaults. Include a two-independent-home fixture journey with known useful drift and safe incomplete comparison; do not export real host state without the specified privacy review or claim live qualification. Keep #53 and paid #138 observations pending.

- [ ] Review canonical document impact, record content-bound dispositions and strict specification/work-record validation.
- [ ] Run the required project checks in the prepared environment and one independent whole-change review; resolve actionable findings with focused reruns, then fresh final CI.
- [ ] Complete implementation checklist based on actual evidence and follow the subsequent archive/merge/exact-merge/finish gates above.
