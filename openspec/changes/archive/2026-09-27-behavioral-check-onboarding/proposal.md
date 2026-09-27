# Behavioral check onboarding

## Why

The [product direction](../../../docs/product-direction.md) promises useful local checks and measured outcomes with small recurring context. The existing runner supports team-owned commands and focused feedback, but adoption does not yet guide a team from its actual test tools to demonstrated behavioral acceptance. The evaluation candidate also lacks the mise runtime required by the normal check path. Passing scaffolding or syntax checks cannot establish that a team's requirement is tested.

## What Changes

- Add a compact inspect, propose, review, prepare and demonstrate path to existing adoption guidance, using the team's tools and existing setup/check services.
- Require reviewed explicit check commands, one observable requirement and a passing/failing/restored-passing rehearsal in an isolated fixture.
- Make the existing mise prerequisite explicit even for generic projects with no tools declared; prepare the evaluation runtime before any later comparison.
- Preserve authored tests, selected checks and complete merged-revision receipt requirements. Distinguish observed check coverage from human judgments of adequacy and product quality.

## Capabilities

### New Capabilities

None; this extends the existing portable-development contract.

### Modified Capabilities

- `portable-development`: add BCO-01 through BCO-05 for behavioral check onboarding and bounded evidence.

## Impact

Audience: adopting team maintainers and harnesses. Likely implementation surfaces: `agents/skills/`, `agents/templates/`, `project-templates/`, `src/ai_dlc/setup/readiness.py`, and existing evaluation image preparation. Existing `src/ai_dlc/setup/project.py` and receipt validation remain authoritative.

Canonical documentation to review: `docs/development-workflow.md`, `docs/workflows/brownfield.md`, `docs/verification/end-to-end-evaluation.md`, and `docs/product-direction.md`. Update applicable mappings in `docs/catalog.toml` and record content-bound dispositions. Do not create a second testing handbook.

No universal test framework, automatic code mutation in the user's worktree, automatic check adequacy score, new runner, release publication or paid #138 execution is included. This is a proposed implementation change; this specification delivery implements none of it.

## Planning review disposition — September 26, 2026

Reviewed against the current implementation, canonical requirements and the user's request to specify and publish the team-adoption recommendations. Scope, compatibility, dependencies and acceptance scenarios are accepted for this planning backlog. Commands and behaviors described as new remain proposed until implemented; no live platform/client qualification, release publication or paid evaluation is claimed. Implementation owner remains unassigned.
