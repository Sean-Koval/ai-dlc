# Validate work record artifact references as a repository invariant

## Context
`artifact_is_local` is pure and provider-neutral by design: it must not interpret a specification provider's identifiers, and an OpenSpec change directory has the same shape as an opaque slash ID such as `organization/spec-id`. The previous tie-breaker was whether the path existed, which the caller established inline. That made the classification depend on the one fact archiving changes.

`ai-dlc work validate <id>` reads the selected dependency closure through `resolve_work`, which recomputes provider fingerprints and refuses on binding drift. That is right immediately before a mutation, but on 2026-09-12 per-record validation refused 39 of this repository's 49 records on provider binding drift alone, because finished records legitimately keep historical fingerprints. The same reader cannot become a repository-wide check.

## Goals / Non-Goals
Report a moved or never-written repository path as an absent local artifact; keep provider-native identifiers untouched; make a dangling reference anywhere in `.ai-dlc/work/` fail a required check. Do not widen this into archiving safety in general: broken documentation links from the same archives are already refused by the documentation gate. Do not validate bindings, probe providers or HTTP(S) references, or change any finish gate.

## Decisions
- Anchor, not leaf. The caller reports whether the reference's leading path segment, such as `openspec` or `docs`, is an entry of the repository root, and the classifier treats an anchored reference as local. The anchor is stable across archiving because archiving moves leaves. An opaque slash ID stays provider-owned unless its first segment collides with a top-level repository entry, in which case it was never unambiguous; a provider URI remains the explicit form for provider ownership and `./` for local ownership.
- The anchor check subsumes the previous dangling-symlink walk: a dangling final or ancestor symlink lives under an existing root entry, so it is anchored and reaches containment validation exactly as before.
- One artifact validator. `validate_artifacts` is shared by the per-record closure reader and the repository-wide reader, so the two cannot drift apart.
- The repository-wide reader validates shape, artifacts and graph only. Bindings are excluded on purpose and the reason is recorded in code: drift is a mutation-time refusal for the record being changed, not a property of the repository.
- `--all` is an explicit flag rather than an implicit no-argument mode so a check manifest line states what it runs. Exactly one of a work ID or `--all` is accepted.
- The project template gains the same required check. A fresh project with no records passes, and `ai-dlc` is already on the path for the template's `generated` check.
- Rejected: treating any slash-bearing reference as local, which would validate `organization/spec-id` as a path and break the TR-03 provider-native scenario. Rejected: asking the specification provider to classify references, which would put filesystem interpretation behind a contract that is deliberately opaque about identifiers.

## Risks / Trade-offs
A provider-native identifier whose first segment equals a top-level repository entry is now validated as a path. No record here has one, and the provider URI form remains available. The repository-wide check reads every record on every `ai-dlc project check`; the current corpus validates in well under a second.

## Migration Plan
No record changes. Every existing record validates under the new rule. Downstream projects that adopt the updated template gain the `work-records` check on their next template sync; projects with an older manifest can add the same command line by hand.
