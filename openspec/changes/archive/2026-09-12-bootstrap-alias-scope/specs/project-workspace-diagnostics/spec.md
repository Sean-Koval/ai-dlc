## MODIFIED Requirements

### Requirement: WD-01 Operational diagnostics
One shared read-only project workspace service SHALL be exposed through CLI
`project workspace-check` and MCP `project_workspace_check`. It SHALL separately
report the PATH-selected executable's lexical and resolved location, its observed
version, the current-process package version and required command availability;
current-process and configured shell activation; the checkout the shared bootstrap
alias runs; canonical source and machine-local mount identity, connectivity
and mounted navigation; and native-client qualification. It SHALL return scoped
findings and limitations without mutation or a single aggregate readiness claim.

The root CLI SHALL expose `--version`. Workspace diagnostics SHALL use bounded,
time-limited `--version` and explicit `--help` probes of the PATH-selected executable
and SHALL NOT substitute current-process package metadata for an unobserved executable
version. Alias attribution SHALL come from the record inside the environment the
alias resolves into and SHALL remain unknown when no such record exists.

#### Scenario: Unactivated or stale setup
- **WHEN** the executable is missing from PATH or a mount points at a missing checkout
- **THEN** diagnostics report actionable scoped findings without mutation or unsupported claims of native readiness

#### Scenario: Configured shell is not active
- **WHEN** the existing AI-DLC-owned shell configuration names the bootstrap bin but the current PATH does not select it
- **THEN** diagnostics distinguish configured-for-next-shell activation from installation and direct the user to the existing activation path without creating another alias or shell entry

#### Scenario: Shell state cannot be proved safely
- **WHEN** activation would require reading outside the relevant owned section or exposing authored shell content
- **THEN** diagnostics report shell activation unverified and return no authored content or possible secrets

#### Scenario: The shared alias runs another checkout
- **WHEN** PATH selects the shared bootstrap alias and the environment it resolves into records a checkout other than this one
- **THEN** diagnostics name that checkout and direct the user to this checkout's own environment or to deliberate alias publication

#### Scenario: The shared alias cannot be attributed
- **WHEN** the environment the alias resolves into records no checkout
- **THEN** attribution is reported as unknown rather than inferred from the environment's name

#### Scenario: Mounted and repository-only links
- **WHEN** a mounted document links to an existing OpenSpec document and to an existing source file outside `docs` and `openspec`
- **THEN** diagnostics report the OpenSpec target as mounted and the source target as repository-only without adding an arbitrary source mount or treating either link as private-note authority

#### Scenario: Project has no mount binding
- **WHEN** the selected machine configuration has a missing, unavailable or unbound vault and the project has no local mount binding
- **THEN** diagnostics report that scoped state without accepting an arbitrary vault override, scanning the vault or creating a binding

#### Scenario: Malformed binding is isolated
- **WHEN** one local binding is malformed or names an unavailable checkout
- **THEN** diagnostics report that binding without following it, broadening filesystem traversal or suppressing independent healthy results

#### Scenario: Filesystem state cannot qualify Obsidian
- **WHEN** mount bindings and links resolve on disk
- **THEN** the diagnostic result keeps native-client qualification not-assessed; observed Obsidian navigation, search, backlinks, external refresh and edit-in-Git evidence is recorded separately and is never inferred by this inspection
