## 1. Review and dependencies
- [x] 1.1 Review NHV-01–NHV-05, selected-client scope, cost/privacy boundary and version-aware activation decisions; record product/engineering disposition.
- [x] 1.2 Integrate the effective-environment-report schema-1 identity contract and completeness rules; do not create a competing source identity.
- [ ] 1.3 Review current official client schema documentation against concrete installed editions/versions and record adapter source/date; leave unobserved recognition pending.

## 2. Native evidence and rendering
- [ ] 2.1 Implement bounded operator evidence schema, harmless marker fixtures, identity validation and read-only agents verification procedure/status surface.
- [ ] 2.2 Add adapter compatibility entries and explicit version-scoped Antigravity rendering metadata with existing ownership/preview/apply preservation.
- [ ] 2.3 Keep configured/rendered/recognized/authenticated statuses separate and invalidate changed contexts without automatic native execution or login.

## 3. Verification and documentation
- [ ] 3.1 Test missing/unrecognized versions, metadata conflict/preservation, wrong markers, stale source/client/guidance/fixture identities, malformed evidence and privacy/cost safeguards.
- [ ] 3.2 Verify existing unversioned rendering and native-tool composition remain compatible and never gain an inferred qualification claim.
- [ ] 3.3 Add the exact manual instruction/skill/MCP procedure and evidence handoff to #53; keep actual unavailable client/Windows walkthrough pending and paid comparison #138 deferred.
- [ ] 3.4 Review machine enrollment, work-computer setup, tool map, onboarding evidence and release verification; record content-bound documentation dispositions and applicable catalog mappings.
- [ ] 3.5 Complete specification/work-record and affected-document review, record required content-bound dispositions, strictly validate this change, run the prepared required checks, and resolve actionable review findings.

## Subsequent delivery gates

After implementation and the checklist above are complete, archive this independently owned change on its bound delivery branch with `ai-dlc work archive`. Repair moved artifact links and any evidence targets actually made stale by archival. Immediately before authorized merge, update from the target branch and refresh required checks/evidence. Finish through `ai-dlc work finish` against the exact merged revision and its configured receipts. These remain mandatory later delivery gates, not checkboxes that must falsely claim post-merge completion before archive. No package publication or paid comparison is authorized by this task list.


## Implementation plan

**Goal:** Give teams a read-only, bounded procedure and evidence check for their selected harness, retaining useful partial observations without inventing qualification.

**Architecture:** Pure adapter/fixture and evidence contracts live under `harness/`; local collection reuses the EER service and safe file boundaries; CLI only parses options and emits the result. Current native compatibility limitations stay explicit. Python/Pydantic/pytest; no new dependency, service, runner or automatic model call.

### Task A — Pure native evidence and procedure contracts
- [ ] Add small `harness/native_adapters.py` for fixed fixture markers, reviewed source metadata, canonical adapter contract identity and explicit compatibility state. No fabricated version entries.
- [ ] Add `harness/native_evidence.py` for strict bounded schema parsing and pure adjudication against parsed EER reports. Separate valid-but-limited evidence from malformed input; no filesystem/process/network access in this module.
- [ ] Cover malformed/oversized/duplicate-key/private sentinel input, wrong markers, missing/duplicate steps, stale identities, known version/platform conflicts, incomplete provenance, independent step results, historical auth and cost boundary. Use descriptive bounded test IDs.
- [ ] Focused tests, scoped checks, self-review and independent task review before integration.

### Task B — Bounded local service and thin CLI
- [ ] Add `harness/native_verification.py` using explicit root/client/report inputs, safe bounded evidence reads, offline EER collection and manual procedure generation. Do not infer probed runtime freshness from a default collection.
- [ ] Add `agents verify --root PATH --client CLIENT --environment REPORT [--evidence FILE]`; require explicit scope and safe errors. The initial draft uses exit1 for valid pending/failed/stale/partial context and exit2 for malformed/refused input. Exit0 qualification remains unimplemented until reviewed compatibility inputs exist; no fabricated success fixture. Unknown versions stay explicit.
- [ ] Test real CLI/file boundaries, no process/network/write effects, stale local safe configuration, missing/modified guidance, incompatible selections, and valid incomplete output. Do not use unbounded renderer reads to establish freshness.
- [ ] Focused integration tests, scoped checks, self-review and independent task review.

### Task C — Version activation boundary, documentation and delivery
- [ ] Record reviewed official contracts and exact installed contexts where available. Positive Antigravity compatibility/render migration remains pending without concrete evidence; preserve all authored files and existing unversioned behavior. Correct the offline readiness next step to request version-specific inspection rather than prescribing historical Always On UI steps universally.
- [ ] Update canonical runbooks/tool map/release and onboarding evidence; record content-bound dispositions/catalog mappings. Hand off actual native walkthrough to #53 with exact steps and remaining limitations. No paid #138 run.
- [ ] Run required checks, whole-change review and review any fixes. If NHV-03 remains unimplemented, publish a draft PR with explicit unchecked acceptance instead of archival/merge/finish. Proceed to independently deliverable next issue only after this bounded work is reviewable and pending context is recorded.
