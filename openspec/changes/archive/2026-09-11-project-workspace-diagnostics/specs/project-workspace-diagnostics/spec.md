## ADDED Requirements

### Requirement: WD-01 Operational diagnostics
One shared read-only project workspace service SHALL be exposed through CLI
`project workspace-check` and MCP `project_workspace_check`. It SHALL separately
report the PATH-selected executable's lexical and resolved location, its observed
version, the current-process package version and required command availability;
current-process and configured shell activation; canonical source and machine-local mount identity, connectivity
and mounted navigation; and native-client qualification. It SHALL return scoped
findings and limitations without mutation or a single aggregate readiness claim.

The root CLI SHALL expose `--version`. Workspace diagnostics SHALL use bounded,
time-limited `--version` and explicit `--help` probes of the PATH-selected executable
and SHALL NOT substitute current-process package metadata for an unobserved executable
version.

#### Scenario: Unactivated or stale setup
- **WHEN** the executable is missing from PATH or a mount points at a missing checkout
- **THEN** diagnostics report actionable scoped findings without mutation or unsupported claims of native readiness

#### Scenario: Configured shell is not active
- **WHEN** the existing AI-DLC-owned shell configuration names the bootstrap bin but the current PATH does not select it
- **THEN** diagnostics distinguish configured-for-next-shell activation from installation and direct the user to the existing activation path without creating another alias or shell entry

#### Scenario: Shell state cannot be proved safely
- **WHEN** activation would require reading outside the relevant owned section or exposing authored shell content
- **THEN** diagnostics report shell activation unverified and return no authored content or possible secrets

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

### Requirement: WD-02 Portable guidance
Canonical and generated guidance SHALL explain organization, local mounts,
repository-only navigation limits, project access, reuse of existing activation
repair and reconciliation of external organizing skills with the selected formal
specification provider.

#### Scenario: Old skill instructions
- **WHEN** an installed external skill proposes docs/specs as a competing formal home
- **THEN** guidance requires reconciliation with OpenSpec rather than creating duplicate specifications; inaccessible work-computer files remain pending

#### Scenario: Existing activation is stale
- **WHEN** installation exists but the current shell or owned activation points at a stale executable
- **THEN** guidance uses existing bootstrap/workstation reconciliation and does not prescribe a redundant symlink or competing shell stanza

### Requirement: WD-03 Qualification evidence
Verification SHALL distinguish automated fixtures, a real harness messy-project
organization exercise, and separately observed native Obsidian
navigation/search/backlinks/external-refresh/edit-in-Git evidence. Unavailable
work-computer, Antigravity or platform checks SHALL remain pending.

#### Scenario: End-to-end exercise
- **WHEN** the workflow is qualified
- **THEN** observed results, exact scope and missing client evidence are recorded honestly without treating passing unit tests as live qualification

#### Scenario: Messy-project exercise is repeated
- **WHEN** a maintainer repeats document organization qualification
- **THEN** a controlled reusable messy-project fixture and canonical manual walkthrough preserve the approved baseline and expected review points without autonomous repository organization or native-client automation
