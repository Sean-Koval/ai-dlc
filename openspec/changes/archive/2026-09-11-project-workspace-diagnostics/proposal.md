# Diagnose and qualify document organization and Obsidian workspace setup

## Why
Existing setup and readiness reports do not show whether the `ai-dlc` executable
selected by the current shell is the expected version, whether the shell is merely
configured for a later session, or whether a local project mount still points at
its recorded checkout. Filesystem links also cannot establish native Obsidian
behavior, and mounted `docs/` and `openspec/` trees do not make other repository
paths available through the vault.

## What Changes
- Add one shared read-only project workspace inspection service, exposed as
  `ai-dlc project workspace-check` and MCP `project_workspace_check`.
- Report executable identity/version/commands, current and configured shell
  activation, machine-local mount identity/connectivity, mounted navigation and
  native-client qualification as separate results without one ambiguous readiness
  claim.
- Canonical and generated guidance SHALL explain organization, local mounts,
  repository-only links, existing activation repair and reconciliation of external
  organizing skills with OpenSpec ownership.
- Verification SHALL distinguish automated fixtures, a real harness messy-project organization exercise, and native Obsidian navigation/search/backlinks/external-refresh/edit-in-Git evidence. Unavailable work-computer, Antigravity or platform checks SHALL remain pending.
- Preserve the deliberately messy project as a reusable controlled fixture with
  canonical manual walkthrough instructions; do not turn diagnostics into an
  autonomous organizer or native-client automation service.

## Capabilities
### New Capabilities
- project-workspace-diagnostics: Diagnose and qualify document organization and Obsidian workspace setup

## Impact
Shared Python documentation services, thin CLI/MCP adapters, portable skills and
existing canonical documentation guidance. The implementation reuses the existing
bootstrap/workstation activation and native-mount bindings; it does not create a
second activation link or broaden mounts beyond `docs/` and existing `openspec/`.
Related prior work: GitHub #32 and #34; their scope and qualification remain
independent. No Jira, vault synchronization or remote publication.
