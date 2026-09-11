# Diagnose and qualify document organization and Obsidian workspace setup

## Context
The user approved the four-deliverable program and native local editable mounts.
Bootstrap already publishes `ai-dlc` and `ai-dlc-cli` aliases in its owned bin
directory, while workstation activation owns the bash/zsh PATH and mise stanza.
Native mount bindings record a stable checkout, vault and project name, and expose
only `docs/` and an existing `openspec/` as sibling directories. Existing doctor
output combines enrollment and provider checks; it does not diagnose this complete
workspace path.

## Goals / Non-Goals
Implement a deterministic local inspection that explains each boundary and gives a
scoped next action. Do not add another activation writer, arbitrary source mounts,
an autonomous relocation engine, vault mirror, Jira integration or changes to
inaccessible company files.

## Decisions
- Add `inspect_project_workspace(root, *, environ=None)` under
  `src/ai_dlc/documentation/`. The CLI `project workspace-check --root .` and MCP
  `project_workspace_check()` are thin adapters over the same result.
- Return schema 1 with `project_root`, `installation`, `activation`, `workspace`,
  `navigation`, `native_client`, `findings` and `limitations`. Each section owns its
  status; do not collapse them into one `ready` boolean.
- `installation` reports PATH lookup, lexical and resolved executable paths, the
  PATH executable's observed version, the current-process package version, and
  availability of the required project document/workspace commands. Add a normal
  root `--version` response so the PATH-selected executable can identify itself.
  Probe only explicit `--version` and `--help` commands with bounded output and a
  short timeout. Never infer the selected executable's version from current-process
  import metadata.
- `activation` distinguishes the current process PATH from the existing AI-DLC-owned
  bash/zsh configuration. Report active, configured-for-next-shell, stale or missing
  state and direct users to restart/source the configured shell or rerun existing
  setup reconciliation. Inspect only the relevant owned section and referenced
  paths; never return authored shell contents or possible secrets. Report activation
  as unverified where ownership or effective shell state cannot be proved. Never
  create or rewrite an alias during inspection.
- `workspace` reads only ignored machine-local mount bindings through
  `read_mount_bindings`. Inspect each binding independently and report canonical
  source identity, source existence, destination, raw link target and resolved-target
  equality for the established `docs` and `openspec` roots. A malformed binding,
  missing checkout or changed link is a scoped finding, not permission to follow or
  repair it. With no binding, report the selected machine configuration's vault as
  unbound, missing or unavailable without accepting an arbitrary vault/name override
  or scanning that vault.
- `navigation` classifies bounded local Markdown targets from canonical repository
  documents by reusing project-document access read/link helpers. Targets within
  working `docs`/`openspec` sibling mounts are `mounted`; existing targets outside
  those roots are `repository-only`; missing targets are `missing`. Outside-mounted
  targets expose safe path/status metadata only: do not read their bodies or fetch
  links. A link such as `docs/reference/...` to `../../src/...` therefore remains
  valid in Git but unavailable through the native mount. Diagnostics do not add a
  `src` mount to compensate.
- `native_client` always reports `not-assessed`. Filesystem connectivity cannot
  establish Obsidian indexing, navigation, search, backlinks, external refresh or
  edit-in-Git behavior; observed walkthrough evidence belongs in the canonical
  verification record.
- Harnesses supply semantic judgment and ordinary Git edits. External organizing
  skills are procedural input: reconcile their useful instructions with existing
  repository conventions and the selected specification provider. In this project,
  proposal, design, requirements and tasks remain under `openspec/changes/`; do not
  create `docs/specs/`, move OpenSpec, or silently accept a conflicting skill rule.
- Preserve existing portal and private-note defaults. Review affected canonical
  guides and record content-bound documentation dispositions.

## Risks / Trade-offs
Command probes must be bounded and read-only, and a stale PATH executable may not
support the new command. Per-binding errors avoid hiding healthy workspaces, but a
malformed binding must not broaden traversal or leak machine paths beyond the local
diagnostic response. Markdown classification can establish filesystem reachability,
not semantic correctness or native-client behavior. Missing client or company
evidence stays explicitly pending.

## Migration Plan
The command is additive and read-only. Reuse existing bootstrap aliases, workstation
activation, mount bindings and portal behavior without migration or new symlinks.
Review exact Git diffs and use existing verification and finish gates.

Keep the approved messy-project input and expected organization outcome as a
controlled reusable test fixture or explicit opt-in fixture builder. Canonical
walkthrough instructions repeat the harness exercise manually; neither the fixture
nor diagnostics autonomously edits a project or drives Obsidian.
