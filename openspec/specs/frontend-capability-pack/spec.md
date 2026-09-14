# frontend-capability-pack Specification

## Purpose
TBD - created by archiving change frontend-capability-pack. Update Purpose after archive.
## Requirements
### Requirement: FE-01 Optional frontend smoke

The node frontend capability SHALL add a Playwright smoke test and required frontend-smoke check. The check SHALL skip successfully with an explicit message when BASE_URL is unset and SHALL never install browsers or packages during checks. A configured smoke SHALL visit the app root, require a nonempty title and capture a screenshot under .ai-dlc/local/design/smoke. Browser and dependency installation SHALL be explicit setup.

#### Scenario: No server configured
- **WHEN** a generated frontend project runs checks without BASE_URL
- **THEN** smoke exits zero with a clear skip message and no browser installation

#### Scenario: A local app is available
- **WHEN** BASE_URL names a running app with a nonempty title
- **THEN** smoke visits it and writes a screenshot

### Requirement: FE-02 Contained capture evidence

Design capture SHALL record PNG files for requested viewports and visible-selector states plus a manifest with URL, capture time, viewports, states and file references inside a repository-contained output directory. Invalid paths, symlinks, unsafe names and existing capture sets SHALL be refused before capture. Failed capture SHALL NOT create a successful manifest.

#### Scenario: Two viewports
- **WHEN** capture runs against a local static page at two viewport dimensions
- **THEN** both screenshots and their manifest entries exist within the selected output directory

#### Scenario: Invalid capture destination
- **WHEN** output escapes the project or traverses a symlink
- **THEN** capture refuses before launching the browser

