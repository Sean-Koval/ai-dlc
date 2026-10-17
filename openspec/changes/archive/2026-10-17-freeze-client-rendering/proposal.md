# Freeze client rendering and replace exact hook version gating

## Why

Hangar renders the configuration that runs in cloud sandboxes at claim time (ADR 0001). AI-DLC's renderer still threaded an unused `target` argument through `render_agents`, `_render_agents` and `render_windows`, and kept `devcontainer`, `codex-cloud` and `claude-cloud` execution targets that no qualification ever covered. Required hooks only rendered when a client's configured version exactly matched a stale fixture (`claude-code` 2.1.0, `codex` 0.151.0), so anyone on a current CLI was refused, while the module catalog installed those same stale versions. Issues #196 and #197.

## What Changes

- Remove the unused `target` parameter from the three render functions.
- Keep only the `local` and `github-actions` execution targets; refuse removed and unknown targets with a message that names the supported targets and hangar. The dev container and the `scripts/cloud/` shims bootstrap with `local`.
- Replace exact-version hook fixtures with a per-client minimum version (`agents/capabilities.toml` schema 2, no `target` key). Below the floor refuses, at or above renders, unset renders with a warning.
- Pin `claude-code` 2.1.296 and `codex` 0.162.1 in the module catalog, copied from hangar's harness lock, and add an offline local `scripts/check_client_pins.py` diff.
- Add a freeze comment above the client table and a line in ADR 0001.

## Capabilities

### New Capabilities

- `client-rendering-freeze`: CR-01 through CR-04.

## Impact

`project setup --target` and `doctor --target` refuse the removed targets. Python callers passing `target=` to `render_agents` break; there is no published API contract. `machine provision` installs newer client versions on new machines; existing installs are not upgraded.
