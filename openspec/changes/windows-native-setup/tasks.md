# Authoritative implementation tasks

All tasks remain unchecked. Dependency: `windows-portable-core` must be delivered before the native path is accepted.

## 1. Verified native bootstrap

- [ ] 1.1 Confirm portable-core contract availability and inventory Windows entry/import/package prerequisites; record Windows 11 x64/local NTFS/PowerShell 5.1 boundary (WNS-01).
- [ ] 1.2 Review official exact Windows uv/mise artifact versions, URLs and hashes plus pinned Python integrity handling; add inert pin data and source/template parity checks without changing supported Unix pins implicitly (WNS-02).
- [ ] 1.3 Implement plan/source/release PowerShell bootstrap, strict inert release.sh parser, digest/cache/archive validation, destination-local staging and safe entry-point publication (WNS-01/WNS-02; amended BP-01).
- [ ] 1.4 Exercise corrupt asset, wrong architecture, manifest expression/duplicate, interrupted install, concurrently running bootstrap and in-use executable cases; preserve selected working CLI and prove retry (WNS-02).

## 2. Native environment and selected tools

- [ ] 2.1 Implement user-local native locations, `.exe`/`Scripts` resolution, checkout-bound source provenance and working alias preservation/explicit publication (WNS-03).
- [ ] 2.2 Implement previewed PowerShell owned activation with policy diagnostics; test authored/modified profile preservation, duplicate prevention and fresh-terminal/direct-path use (WNS-03).
- [ ] 2.3 Add core Git/GitHub CLI and pinned Python provisioning plans, exact winget package identity, installed-version readback and no-upgrade behavior; provide absent/blocked-manager recovery (WNS-04).
- [ ] 2.4 Report selected/implied unsupported modules individually and enforce truthful incomplete readiness without installing unselected tools or authenticating accounts (WNS-04).

## 3. Consumer project journey

- [ ] 3.1 Generate native argv management/Python checks and bounded conditional Python setup; preserve noninitializing adoption, existing locks/tests, authored commands and generic project autonomy (WNS-05).
- [ ] 3.2 Verify source and packaged scaffold contain native bootstrap assets and the correct manifest propagation; require a compatible engine for argv templates (WNS-02/WNS-05).
- [ ] 3.3 Run generic team-owned and Python starter behavior with deliberate regressions, missing/all-skipped tests, missing runtime, repeated setup and edited managed-file conflict on Windows and retained Unix targets (WNS-05).

## 4. Platform and release evidence

- [ ] 4.1 Add native Windows CI jobs and explicit required checks/receipt artifact bindings; retain Unix matrix and justify platform-specific skips without reducing Windows acceptance (WNS-06).
- [ ] 4.2 Add candidate and read-only published-asset Windows consumer verification for both minimal seed and generated project, exact wheel/constraints/manifest identity and clean required check receipts (WNS-06).
- [ ] 4.3 Obtain a clean Windows 11 x64 account and run the full PowerShell qualification/recovery matrix; record identity/outcomes and extend existing platform qualification tracking with real evidence (WNS-07).
- [ ] 4.4 Review/update canonical setup, contributor/consumer routing, selected module limits and release docs; maintain package/template parity and record content-bound documentation dispositions (WNS-08).
- [ ] 4.5 Complete specification/work-record and affected-document review, record required content-bound dispositions, strictly validate this change, run the prepared required checks, and resolve actionable review findings.

## Subsequent delivery gates

After implementation and the checklist above are complete, archive this independently owned change on its bound delivery branch with `ai-dlc work archive`. Repair moved artifact links and any evidence targets actually made stale by archival. Immediately before authorized merge, update from the target branch and refresh required checks/evidence. Finish through `ai-dlc work finish` against the exact merged revision and its configured receipts. These remain mandatory later delivery gates, not checkboxes that must falsely claim post-merge completion before archive. No package publication or paid comparison is authorized by this task list.
