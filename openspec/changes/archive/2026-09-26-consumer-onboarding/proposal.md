## Why

A teammate installing AI-DLC to use in another repository is currently directed through the engine checkout's contributor bootstrap and full engine checks. The [approved product promise](../../../docs/product-direction.md) requires selected tools and guidance in the teammate's own project. README's source route, the Windows rejection in `setup/provision.py`, and POSIX bootstrap are observed limitations; the teammate's original terminal failure was not observed.

## What Changes

- Add a read-only, project-scoped onboarding preflight and ordered recommendation plan that composes existing enrollment, adoption, setup, rendering and readiness services.
- Separate consumer engine installation, reviewed profile enrollment and target-project adoption from AI-DLC source contribution.
- Make OS, architecture, shell, selected client, target root and source/ref explicit; identify unavailable support and missing inputs before giving executable actions.
- Deliver on supported Unix platforms now with an honest unsupported native-Windows branch. Native Windows support is separately deliverable and is not a prerequisite for this change.

## Capabilities

### New Capabilities
- `consumer-onboarding`: CO-01 through CO-05, a bounded consumer route and non-mutating plan.

### Modified Capabilities
None. Existing enrollment, adoption, project readiness and preservation contracts remain authoritative; additive composition does not change their mutation semantics.

## Impact

Candidate implementation areas: `src/ai_dlc/setup/`, a thin CLI entry point, bootstrap-facing documentation and downstream guidance. Canonical docs to review: [README](../../../README.md), [machine enrollment](../../../docs/runbooks/machine-enrollment.md), [work-computer setup](../../../docs/workflows/work-computer-setup.md), [tool map](../../../docs/workflows/tool-map.md), [release limits](../../../docs/release-verification.md), and applicable packaged guidance. Existing owners retain authority; no parallel onboarding guide is proposed. Implementation must record content-bound documentation dispositions and update catalog mappings only if affected ownership changes.

## Authorization and review status

The user authorized preparing specifications and detailed delivery issues from the PM review, including improving teammate onboarding. This proposal's command shape and schema are recommended technical design for review, not approval to implement or a claim of shipped support. Product owner: Sean Koval; implementation owner unassigned. Priority P0. No implementation, live qualification, release publication or provider mutation is performed here. Review status: engineering scope and specification reviewed for planning/publication; implementation has not started.

## Dependencies and exclusions

No dependency on Windows setup/runtime delivery. Later Windows capability can make the same preflight supported without changing its contract. Excludes a hosted orchestrator, new installer, automatic OAuth, paid evaluation, automatic package/client/config writes, personal tracker/vault inheritance, and implicit WSL or Linux-container fallback. The qualification walkthrough remains issue #53.

## Planning review disposition — September 26, 2026

Reviewed against the current implementation, canonical requirements and the user's request to specify and publish the team-adoption recommendations. Scope, compatibility, dependencies and acceptance scenarios are accepted for this planning backlog. Commands and behaviors described as new remain proposed until implemented; no live platform/client qualification, release publication or paid evaluation is claimed. Implementation owner remains unassigned.
