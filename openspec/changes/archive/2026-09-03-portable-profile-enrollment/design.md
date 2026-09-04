## Context

This change implements the approved [portable profile and machine enrollment
design](../../../../docs/superpowers/specs/2026-09-03-portable-profile-enrollment-design.md).
It turns existing configuration and setup primitives into a local-first,
reproducible enrollment workflow: a Git profile supplies shared desired state and
each enrolled machine supplies only its local bindings.

## Goals / Non-Goals

**Goals:**

- Enroll a secret-free profile from an exact Git revision and preserve that pinned
  revision for offline use.
- Let two machines share profile choices while using different paths and
  credential environment-variable names.
- Keep lifecycle changes preview-first and preserve the active enrollment when a
  candidate, reconciliation, or source operation fails.
- Retain current schema-4 configuration and explicit CLI entry points.

**Non-Goals:**

- Store, synchronize, print, or back up secret values.
- Configure password managers, keychains, cloud secret stores, Obsidian Sync,
  tracker discovery, arbitrary profile installation commands, or a hosted control
  plane.
- Claim cloud equivalence or release readiness from local or fixture verification.

## Decisions

### Ownership layers

Five ownership layers remain distinct:

1. A user-controlled Git profile bundle owns portable tool, MCP, workflow, and
   provider preferences.
2. The project repository owns shared project configuration and policy.
3. The local machine binding owns paths, account selections, and credential
   environment-variable names.
4. External credential providers or the process environment own credential
   values; AI-DLC only carries logical identifiers and variable names.
5. Codex and Claude user/project configuration owns generated client files, which
   AI-DLC re-renders through existing ownership protections rather than copying.

Enrollment locks, profile caches, and operation journals are local AI-DLC control
state: useful for recovery and inspection, never a portable source of authority.

### Lock, cache, and transaction model

The active enrollment lock records the profile identity, source, requested ref,
resolved 40-character commit, content digest, machine ID, and selected relative
profile path. Cached content is an immutable materialized profile file keyed by
profile identity and resolved commit, without Git metadata or unrelated source
files. Source resolution validates the profile and digest before cache activation.

Enroll and sync create and validate a candidate first. They preview by default;
with `--apply`, reconciliation runs against the verified candidate and the lock is
atomically activated last. A failed fetch, validation, cache-integrity check, or
reconciliation leaves the prior active lock byte-for-byte unchanged. The verified
active cache remains usable offline.

### Resolution, credentials, and boundaries

Configuration precedence is fixed: packaged base, enrolled personal profile,
project `ai-dlc.toml`, then enrolled machine binding. Explicit `--profile` and
`--machine` files replace the enrolled file only in the matching layer; they do
not add a higher-precedence scope. Provenance remains available for resolved
values, and machine settings cannot weaken project policy.

Profiles declare stable logical credential requirements; machine bindings map them
only to `source = "environment"` and a variable name. Values are never accepted,
persisted, logged, returned, or copied. Existing provider `token_env` settings are
normalized for compatibility.

The CLI remains a parser and result serializer. Focused services resolve profile
sources, persist enrollment state, report credential presence, resolve
configuration, and compose planning, setup, client rendering, and readiness. MCP
does not expose enrollment mutation in this cycle; read-only status is deferred
until the CLI contract settles.

### Compatibility strategy

The implementation preserves schema 4 for base, personal, project, and machine
files; enrollment locks use schema 1. Existing `setup plan`, `setup apply`,
`profile show`, `doctor`, and explicit `--machine` / `--profile` interfaces route
through the compatible resolver and reconciler. `machine migrate` supports a
temporary legacy personal profile path while canonical profiles use
`ai-dlc-profile.toml` and declare `profile_id`.

## Risks / Trade-offs

Git sources and cache integrity add local complexity, but exact commits,
digest-verified materialization, and preview-first activation make changes
reviewable and safely recoverable. Package managers can still leave partial
external installation effects; AI-DLC reports the failed step while protecting its
own lock/cache metadata and existing client ownership rules. Live provider and
clean-target verification remain explicit release gates.
