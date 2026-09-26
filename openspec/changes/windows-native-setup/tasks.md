# Authoritative implementation tasks

Implementation authorized September 26, 2026. Dependency `windows-portable-core` was merged in PR #181 and completed through AI-DLC at revision `3a60d3a4d956a5919357c3f262de740f01d3ecf7`; all six merge-commit CI jobs passed. Checkboxes remain evidence-bound. Clean Windows 11 qualification is pending a suitable host, separately from hosted Windows Server CI.

## 1. Verified native bootstrap

- [x] 1.1 Confirm portable-core contract availability and inventory Windows entry/import/package prerequisites; record Windows 11 x64/local NTFS/PowerShell 5.1 boundary (WNS-01).
- [x] 1.2 Review official exact Windows uv/mise artifact versions, URLs and hashes plus pinned Python integrity handling; add inert pin data and source/template parity checks without changing supported Unix pins implicitly (WNS-02).
- [x] 1.3 Implement plan/source/release PowerShell bootstrap, strict inert release.sh parser, digest/cache/archive validation, destination-local staging and safe entry-point publication (WNS-01/WNS-02; amended BP-01).
- [ ] 1.4 Exercise corrupt asset, wrong architecture, manifest expression/duplicate, interrupted install, concurrently running bootstrap and in-use executable cases; preserve selected working CLI and prove retry (WNS-02).

## 2. Native environment and selected tools

- [x] 2.1 Implement user-local native locations, `.exe`/`Scripts` resolution, checkout-bound source provenance and working alias preservation/explicit publication (WNS-03).
- [ ] 2.2 Implement previewed PowerShell owned activation with policy diagnostics; test authored/modified profile preservation, duplicate prevention and fresh-terminal/direct-path use (WNS-03).
- [x] 2.3 Add core Git/GitHub CLI and pinned Python provisioning plans, exact winget package identity, installed-version readback and no-upgrade behavior; provide absent/blocked-manager recovery (WNS-04).
- [x] 2.4 Report selected/implied unsupported modules individually and enforce truthful incomplete readiness without installing unselected tools or authenticating accounts (WNS-04).

## 3. Consumer project journey

- [x] 3.1 Generate native argv management/Python checks and bounded conditional Python setup; preserve noninitializing adoption, existing locks/tests, authored commands and generic project autonomy (WNS-05).
- [x] 3.2 Verify source and packaged scaffold contain native bootstrap assets and the correct manifest propagation; require a compatible engine for argv templates (WNS-02/WNS-05).
- [x] 3.3 Run generic team-owned and Python starter behavior with deliberate regressions, missing/all-skipped tests, missing runtime, repeated setup and edited managed-file conflict on Windows and retained Unix targets (WNS-05).

## 4. Platform and release evidence

- [x] 4.1 Add native Windows CI jobs and explicit required checks/receipt artifact bindings; retain Unix matrix and justify platform-specific skips without reducing Windows acceptance (WNS-06).
- [x] 4.2 Add candidate and read-only published-asset Windows consumer verification for both minimal seed and generated project, exact wheel/constraints/manifest identity and clean required check receipts (WNS-06).
- [ ] 4.3 Obtain a clean Windows 11 x64 account and run the full PowerShell qualification/recovery matrix; record identity/outcomes and extend existing platform qualification tracking with real evidence (WNS-07).
- [x] 4.4 Review/update canonical setup, contributor/consumer routing, selected module limits and release docs; maintain package/template parity and record content-bound documentation dispositions (WNS-08).
- [ ] 4.5 Complete specification/work-record and affected-document review, record required content-bound dispositions, strictly validate this change, run the prepared required checks, and resolve actionable review findings.

## Subsequent delivery gates

After implementation and the checklist above are complete, archive this independently owned change on its bound delivery branch with `ai-dlc work archive`. Repair moved artifact links and any evidence targets actually made stale by archival. Immediately before authorized merge, update from the target branch and refresh required checks/evidence. Finish through `ai-dlc work finish` against the exact merged revision and its configured receipts. These remain mandatory later delivery gates, not checkboxes that must falsely claim post-merge completion before archive. No package publication or paid comparison is authorized by this task list.

## Execution interfaces and validation

- Native bootstrap owns `scripts/bootstrap.ps1` and mirrored `bootstrap/windows.json`, `windows.ps1`, `windows-native.cs`, `windows-select.py`. The first stage protects publication before verified Python exists; later selection reuses the existing Python native transaction service. Cache paths always revalidate hashes. Per-checkout environments retain native launcher/interpreter identity; the shared selection manifest binds source provenance and launcher digest.
- Existing environment/provision/workstation services own native locations, explicit selected PowerShell profile activation, selected core/Python support and honest unavailable-module/manual-install results. No elevation, authentication or execution-policy change is implied.
- Project templates own portable generic/Python command records and a bounded helper distinguishing initialization from adoption. Checks require a prepared interpreter and cannot create an environment; missing/all-skipped tests remain failures.
- Contributor command records use native argv. Repository scripts adapt only platform-specific pytest coverage and the type-check interpreter; the engine keeps its existing command contract. Windows CI adds explicit native required receipts, source cold-start, and candidate consumption from exact built wheel/constraints caches without publication.
- Focused cases live in `test_windows_bootstrap.py`, `test_windows_environment.py`, `test_windows_provision.py`, `test_native_templates.py`, `test_native_repository_checks.py` and `test_windows_consumer.py`. Retain the #171 native safety suite and full Unix suite. Any skipped required native or clean-account case remains unqualified.

## Evidence and remaining acceptance

Implementation checkboxes bind to the reviewed source and native tests. At branch revision `8eba405883b7d102023d5b07e95bb7249f456a99`, Verify run `36266151124` passed all seven jobs, including 207 native tests with five Unix-only skips and six clean required receipts for PR test-merge revision `dcc4664d90c8c47c32a3e2ff8210dd96b026aaa2`. Candidate run `36266148886` passed the bare seed and generic/Python installed-wheel journeys without publication; exact artifacts and qualification limits are recorded in `docs/release-verification.md`. The older local required-check run overlapped worktree edits and is feedback only, not exact-revision completion evidence.

Full-bootstrap interruption and concurrent-process recovery (1.4), human fresh-terminal profile/runtime resolution (2.2), and clean Windows 11 qualification (4.3) remain unobserved. The machine-enrollment walkthrough provides explicit steps. Provisioning protocols pass real subprocess byte-output regressions under a forced CP1252 default, including malformed-output refusal; mocked package plans do not establish live winget installation. Final acceptance/review (4.5), archival, merge and work finish remain pending those observed qualification requirements. Published replay is implemented but the incompatible historical v0.4.0 release cannot supply successful native evidence.
