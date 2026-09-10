## Why

Project documentation must be discoverable without creating duplicate specifications,
copying private notes into repositories, or granting filesystem access based on a
folder name. PR #28's initial symlink implementation violated these boundaries.
The maintainer authorized a single-source documentation repair.

## What Changes

- Replace the folder-first five-pillar preset with optional organized navigation,
  preserving existing layouts and pointing to canonical OpenSpec artifacts.
- Add an explicit document catalog and read-only CLI/MCP diagnostics for ownership,
  provenance, coverage, duplicate bodies, broken local links and review metadata.
- Integrate document and portal previews into the shared adoption service.
- Replace unsafe directory mounting with a machine-local Markdown project portal.
  Existing mounts are preserved for manual inspection; personal note APIs remain
  confined to the vault. Direct editing of repository docs inside the main vault
  is not provided by this portal.
- Provide portable upkeep guidance and preserve authored content through exclusive
  no-follow creation. No automatic cleanup, publication, synchronization, connector
  or tracker substitution is introduced.

## Capabilities

### New Capabilities
- `obsidian-vault-linking`: canonical documentation organization and local portal setup.

### Modified Capabilities
- None.

## Impact

Shared adoption, knowledge filesystem boundaries, CLI and MCP, optional document
setup, portable guidance and tests. The original PR's force-replace symlink behavior
is intentionally withdrawn before release. Actual Obsidian client behavior and the
custom Confluence MCP remain separate qualification boundaries.
