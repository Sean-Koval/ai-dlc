# Exclude evidence policy from provider identity fingerprints

## Why
`resolve_work` hashes the whole `[scm]` table into the SCM identity, the deployment identity and any `github-issues` tracker identity. In this repository that is three of the five bindings on every work record. `scm.receipt_artifacts` is in that table, but the finish gate never consults the bound value: `GitHubSCM.ci` re-reads `ai-dlc.toml` at the merged revision and takes the expected receipt names from there, so the fingerprint over receipt policy authenticates nothing.

On 2026-09-12 renaming one receipt artifact for the arm macOS runner, commit `587d2d8`, drifted the SCM, deployment and tracker bindings on all 46 work records and blocked `ai-dlc work finish` mid-delivery. Commit `b6652ae` cleared the drifted lines on the two records that had to finish. Reconstructing every stored binding from the pre-rename configuration confirms receipt policy was the only input that differed on all 46 records: the cost was pure, and no identity had actually changed.

`scm.repository`, `scm.target_branch` and `scm.workflow` are different. `GitHubSCM` reads all three from the runtime configuration to decide which repository, which branch and which workflow's runs may be trusted, so they remain identity.

## What Changes
- Provider identity SHALL be projected over SCM configuration excluding receipt artifact policy.
- Changing the receipt matrix SHALL NOT drift any binding, and existing work SHALL finish without rebinding.
- A repository, target branch or workflow change SHALL still refuse mutation with provider binding drift.
- An unrecognised SCM configuration key SHALL still contribute to identity, so new configuration cannot silently bypass the guard.
- Delivery guidance SHALL stop claiming the fingerprint protects receipt authentication.

## Capabilities
### Modified Capabilities
- spec-delivery-traceability: Provider identity covers trusted-service configuration and excludes receipt artifact policy.

## Impact
Work provider resolution, the canonical development workflow and their tests. Every record's SCM, deployment and tracker fingerprint changes once; the in-flight records whose drift is proven to be receipt policy alone are rebound in this change, and finished records keep their historical fingerprints. No gate is relaxed: receipts are still authenticated against the merged manifest, and no evidence requirement changes.
