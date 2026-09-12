# Exclude evidence policy from provider identity fingerprints

## Implementation
- [x] 1.1 Project provider identity over SCM configuration excluding receipt artifact policy, with regression tests covering a receipt matrix change and a repository, target branch and workflow change.
- [x] 1.2 Cover an unrecognised SCM configuration key still drifting bindings, so the exclusion cannot become a bypass.
- [x] 1.3 Confirm the deployment table holds no evidence policy and keep its identity whole, with a regression test.
- [x] 2.1 Rebind the in-flight records whose drift is proven to be receipt policy alone.
- [x] 2.2 Correct the canonical development workflow so it no longer claims the fingerprint authenticates receipts.

## Verification and delivery
- [x] 9.1 Record documentation-impact dispositions for the change.
- [x] 9.2 Validate this OpenSpec change and run required project checks.
- [x] 9.3 Update from the target branch, review the pull request, merge with fresh checks and verify merged-revision CI receipts.
