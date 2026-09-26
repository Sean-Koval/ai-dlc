## 1. Contract review
- [ ] 1.1 Review EER-01–EER-05, schema/CLI compatibility, desired-field allowlist, completeness semantics and drift classes; record product/engineering disposition.
- [ ] 1.2 Map pure local collectors from status/readiness/workspace diagnostics and version/provenance adapters; enumerate unsupported provenance rather than infer it.

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
