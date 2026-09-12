# Explain and document finishing work after the target branch moves

## Why
`ai-dlc work finish` requires the local checkout to be exactly the pull request's merge commit with a clean `openspec/` tree. Once the target branch moves on, finishing from the main checkout is blocked with `OpenSpec checkout revision must equal the merged revision`, which names neither the required commit nor the current one, and the procedure is undocumented. On 2026-09-11 finishing #29-#34, delivered by PR #35 and merged as `b7c6fdb` on 2026-09-10, was blocked from `main` at `687e0e5`; all six finished only after creating a temporary detached worktree at `b7c6fdb`.

## What Changes
- A blocked specification gate SHALL name the expected merged revision, the current checkout revision and the remedy.
- Canonical and generated delivery guidance SHALL describe finishing work after the target branch moved.
- The gate SHALL still refuse a checkout that is not exactly the merged revision or has dirty OpenSpec files.

## Capabilities
### Modified Capabilities
- spec-delivery-traceability: The merged-revision specification gate explains what a matching checkout requires.

## Impact
The OpenSpec provider's merged-revision evidence messages, the canonical development workflow, the generated shared project guidance and their tests. No gate strictness, evidence requirement or tracker behavior is relaxed, and no checkout is created automatically.
