# Publish a versioned AI-DLC release with bootstrap artifacts

## Implementation
- [ ] 1.1 Extend the release workflow: candidate build on manual dispatch unchanged; on a `v*` tag, verify the tag matches the engine version, build, verify installation and scaffolding, generate the manifest against the release download URL, publish the assets with a checksum file, then bootstrap a throwaway project from the published assets.
- [ ] 1.2 Release-mode bootstrap retains `bootstrap/release.sh` beside the installed engine, in both the repository script and its packaged template copy, with a regression test on the release fixture.
- [ ] 1.3 Project generation includes `bootstrap/release.sh` from the running engine's retained manifest and reports `release_manifest` as included or absent, with tests for both.
- [ ] 2.1 Add the release runbook, update the README install section and the template guidance, enrol the runbook in the catalog.
- [ ] 2.2 Record the local release-mode proof and the evidence boundary in `docs/release-verification.md`.

## Verification and delivery
- [ ] 9.1 Record documentation-impact dispositions for the change.
- [ ] 9.2 Validate this OpenSpec change and run required project checks.
- [ ] 9.3 Update from the target branch, review the pull request, merge with fresh checks and verify merged-revision CI receipts.
