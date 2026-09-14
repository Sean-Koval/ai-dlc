# Publish a versioned AI-DLC release with bootstrap artifacts

## Implementation
- [x] 1.1 Extend the release workflow: candidate build on manual dispatch unchanged; on a `v*` tag, verify the tag matches the engine version, build, verify installation and scaffolding, generate the manifest against the release download URL, publish the assets with a checksum file, then bootstrap a throwaway project from the published assets.
- [x] 1.2 Release-mode bootstrap retains `bootstrap/release.sh` beside the installed engine, in both the repository script and its packaged template copy, with a regression test on the release fixture.
- [x] 1.3 Project generation includes `bootstrap/release.sh` from the running engine's retained manifest and reports `release_manifest` as included or absent, with tests for both.
- [x] 2.1 Add the release runbook, update the README install section and the template guidance, enrol the runbook in the catalog.
- [x] 2.2 Record the local release-mode proof and the evidence boundary in `docs/release-verification.md`.

## Verification and delivery
- [x] 9.1 Record documentation-impact dispositions for the change.
- [x] 9.2 Validate this OpenSpec change and run required project checks.
- [x] 9.3 Update from the target branch, review the pull request, merge with fresh checks and verify merged-revision CI receipts.

Delivery evidence: PR #88 merged at `f1becc4b417622a8ca1853275c562c5ce1f90df0`; Verify run `34771458251` supplied all five clean merged-revision receipts with all eight required checks passing. This previously unchecked delivery item is finalized by a corrective follow-up; the original merge is unchanged. Canonical publication, replay and qualification boundaries remain in `docs/release-verification.md`.
