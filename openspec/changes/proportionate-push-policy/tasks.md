## 1. Project policy and compatibility

- [ ] 1.1 Add configuration cases for omitted/default policy, both supported values, invalid types/values and personal/machine/team-source attempts to supply the field; inspect `src/ai_dlc/config.py` and existing configuration tests.
- [ ] 1.2 Implement project-only `agents.bound_push_policy` validation and default all-branches semantics without enabling hooks or changing client capability fixtures.

## 2. Offline branch classification

- [ ] 2.1 Add temporary-repository hook cases for a valid bound branch, multiple valid matching records, one invalid match among valid records, unreviewed/missing-tracker/provider-drifted records, unreadable inventory, detached identity and a truly unbound branch in both modes.
- [ ] 2.2 Update `src/ai_dlc/harness/hooks.py` using existing offline work validation; require every matching record to be valid, reviewed and tracker-bound, and allow a truly unbound branch only in explicit tracked-branches mode.
- [ ] 2.3 Verify no provider calls/journals or synthetic work records are created; retain existing destructive denials, ordinary payload results and unsupported-payload coverage.

## 3. Guidance, evidence and delivery

- [ ] 3.1 Update applicable generated guidance/config examples and canonical small-change instructions to state the selected policy; verify no-hook configurations acquire no new record requirement.
- [ ] 3.2 Run the real hook service against isolated Git fixtures, label native fixture coverage honestly and record the strict/default multi-record regression result.
- [ ] 3.3 Complete specification/work-record and affected-document review, record required content-bound dispositions, strictly validate this change, run the prepared required checks, and resolve actionable review findings.

## Subsequent delivery gates

After implementation and the checklist above are complete, archive this independently owned change on its bound delivery branch with `ai-dlc work archive`. Repair moved artifact links and any evidence targets actually made stale by archival. Immediately before authorized merge, update from the target branch and refresh required checks/evidence. Finish through `ai-dlc work finish` against the exact merged revision and its configured receipts. These remain mandatory later delivery gates, not checkboxes that must falsely claim post-merge completion before archive. No package publication or paid comparison is authorized by this task list.
