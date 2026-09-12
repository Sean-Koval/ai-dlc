# Exclude evidence policy from provider identity fingerprints

## Context
A binding records which provider a work record was reviewed against, and a mismatch refuses mutation so nobody silently retargets reviewed work at a different service. The SCM table mixes two kinds of configuration. `repository`, `target_branch` and `workflow` are read from the runtime configuration by `GitHubSCM` and decide which repository, branch and workflow runs are trusted, so they are identity. `receipt_artifacts` and the legacy `receipt_artifact` are evidence policy: `GitHubSCM.ci` reads them from `ai-dlc.toml` at the merged revision, never from the bound configuration, so hashing them into identity protects nothing while invalidating every record whenever the CI matrix changes.

## Goals / Non-Goals
Stop evidence policy from drifting bindings while keeping every genuine identity change refusing. Do not weaken receipt authentication, which continues to use the merged manifest; do not pre-clear bindings on finished work; do not add dual-hash compatibility logic.

## Decisions
- Exclude the known evidence-policy keys rather than whitelisting the identity keys. A whitelist would silently ignore a future key such as an enterprise `scm.host`, which must drift bindings. Excluding named keys keeps the fail-safe default: unrecognised configuration still contributes to identity.
- Keep the deployment table whole. `GitHubSCM.deployment` reads both `deploy.workflow` and `deploy.environment` from the runtime configuration to decide which deployment is trusted, so neither is evidence policy and there is nothing to exclude.
- Exclude the legacy singular `receipt_artifact` alongside `receipt_artifacts`, because `ci` falls back to it from the merged manifest on the same terms.
- Rebind in one reviewed commit rather than bumping the work schema to accept two hashes. Every stored binding was verified to reconstruct from the pre-rename configuration, which proves receipt policy was the only differing input, so the rebind is evidence-backed rather than a blanket approval. A schema bump would add permanent dual-hash logic for a one-time event.
- Rebind only the records that can still be mutated: the three whose OpenSpec change has unfinished tasks, and this change's own record. Finished records keep their historical fingerprints, which continue to record what they were reviewed against.
- Rejected: keeping the fingerprint and documenting the churn. The previous guidance justified the refusal as protecting receipt authentication, which the code does not do, so the churn had no safety to trade against.

## Risks / Trade-offs
Every record's SCM, deployment and tracker fingerprint changes once, so resuming a finished record still meets a drift refusal and the documented review-and-clear remedy still applies. A future evidence-policy key added to `[scm]` must be added to the exclusion set or it will drift bindings; that failure is conservative and visible rather than silent.

## Migration Plan
Clear the SCM, deployment and tracker binding lines on `portable-development-v4`, `repository-organization`, `selective-tracker-migration` and `provider-identity-projection` so they recompute under the projection. Leave every other record untouched.
