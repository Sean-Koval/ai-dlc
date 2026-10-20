# client-rendering-freeze Specification

## Purpose
Keep ai-dlc client rendering to local repositories and CI, leave cloud sandbox rendering to hangar, gate required hooks on a client version floor rather than exact fixtures, and keep client pins aligned with hangar's harness lock.
## Requirements
### Requirement: CR-01 Execution targets are local and CI only
`project setup --target` and `doctor --target` SHALL accept only the `local` and `github-actions` execution targets. Any other target, including the removed `devcontainer`, `codex-cloud` and `claude-cloud`, SHALL be refused before any setup step, journal write or render, with a message that names the supported targets and, for cloud targets, that hangar renders cloud sandboxes at claim time.

#### Scenario: A removed cloud target is requested
- **WHEN** `ai-dlc project setup --target codex-cloud` runs
- **THEN** it refuses with "cloud sandboxes are rendered by hangar at claim time" and the supported targets, and no setup journal is created

#### Scenario: CI setup checks staleness without applying
- **WHEN** `ai-dlc project setup --target github-actions` runs with stale generated files
- **THEN** rendering is not applied and setup refuses until the generated files are rendered and committed

### Requirement: CR-02 Client rendering is frozen
Client rendering SHALL take no execution-target argument and SHALL produce the same output for the same project configuration. No new client, client format or per-runtime translation SHALL be added to the renderer; the existing `claude-code`, `codex` and `antigravity` clients remain supported for local repositories.

#### Scenario: Render has a single signature
- **WHEN** a caller inspects `render_agents`, `_render_agents` or `render_windows`
- **THEN** none of them accepts a `target` parameter

### Requirement: CR-03 Required hooks check a client version floor
Required hooks SHALL render when every required hook is supported by the selected client and the configured client version is at or above that client's minimum version in the packaged hook table. A version below the floor or that does not start with a dotted integer SHALL refuse before any write with "requires <client> >= <floor>". An unset version SHALL render with a warning naming the assumed floor. The hook table SHALL state that it is not a qualification record, and targets without hook support SHALL report every required hook as unavailable.

#### Scenario: A current client version renders
- **WHEN** `[agents.clients.claude-code] version = "2.1.296"` and `required_hooks = ["stop-reminder"]`
- **THEN** `ai-dlc agents render --check` succeeds after rendering

#### Scenario: An old client version refuses
- **WHEN** `[agents.clients.claude-code] version = "1.9.0"` requires a hook
- **THEN** rendering refuses with "requires claude-code >= 2.1.0" and writes nothing

#### Scenario: An unset version warns
- **WHEN** a client requires a hook and has no configured version
- **THEN** rendering succeeds and the result carries a warning naming the floor

### Requirement: CR-04 Client pins follow hangar's harness lock
The module catalog SHALL pin the `claude-code` and `codex` CLI versions recorded in hangar's `harnesses.lock.yaml`, with a comment naming the source and date. An offline local script SHALL compare the catalog with a given lock file and exit non-zero listing every difference. CI SHALL NOT fetch the lock.

#### Scenario: Pins are compared locally
- **WHEN** `python scripts/check_client_pins.py --hangar-lock PATH` runs against a lock that matches the catalog
- **THEN** it exits 0, and it exits 1 naming each client whose version differs otherwise

