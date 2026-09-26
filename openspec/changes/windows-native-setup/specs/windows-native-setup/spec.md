## ADDED Requirements

### Requirement: WNS-01 A bounded native PowerShell entry point
AI-DLC SHALL provide a native PowerShell bootstrap for Windows 11 x64/local NTFS, usable from inbox Windows PowerShell 5.1 without preinstalled Python, uv, mise, AI-DLC, WSL, Git Bash or a POSIX shell. It SHALL expose plan/source/release, root, target and explicit alias-publication choices equivalent to existing Unix semantics. Plan SHALL be nonmutating. Unsupported architecture, filesystem or policy constraints SHALL be named rather than causing a mandatory WSL route or silent policy change.

#### Scenario: A fresh native account requests a plan
- **WHEN** a Windows 11 x64 account runs the supplied PowerShell entry with plan mode and no toolchain installed
- **THEN** it shows native prerequisites, exact versions/sources, destinations, selected limitations and activation effects without downloading or changing files

#### Scenario: A fresh native account installs the supported path
- **WHEN** that account applies a valid verified plan with permitted native execution and network access
- **THEN** the selected engine and core/Python prerequisites become usable through native executables without starting a POSIX environment

#### Scenario: The host is outside the contract
- **WHEN** the bootstrap sees Windows ARM64, an unsupported storage location or an execution policy that blocks its action
- **THEN** it reports the specific boundary and an explicit supported/manual next step without disabling the policy or claiming installation success

### Requirement: WNS-02 Pinned verified assets and recoverable publication
Native bootstrap SHALL pin supported prerequisite versions and architecture, verify configured hashes before using cached/downloaded uv/mise or engine artifacts, require trusted Python integrity handling, and enforce hashed release dependencies. It SHALL consume the existing release manifest as strictly validated inert data, retain and propagate its exact bytes, and reject missing, corrupt or executable manifest content. Native source environments SHALL retain their checkout identity; no source environment without a manifest SHALL claim verified release bootstrap. Publication SHALL use independently staged owned files and retain the prior working CLI selection on failure, including Windows sharing violations.

#### Scenario: Verified release assets initialize a generated project
- **WHEN** native release bootstrap installs from a valid pinned manifest and that engine initializes a project
- **THEN** the project carries the byte-identical manifest and its native bootstrap selects the same verified engine/constraints identity

#### Scenario: Cache, download or manifest content is unsafe
- **WHEN** a digest mismatches, an archive escapes its extraction root, or a manifest includes duplicate/malformed keys or executable expressions
- **THEN** bootstrap rejects the content before execution/publication and preserves the previously selected working CLI

#### Scenario: Publication is interrupted or blocked
- **WHEN** install/publication fails, a second bootstrap competes, or an open handle prevents replacement
- **THEN** no partial executable becomes selected, independent staging cannot consume another invocation's bytes, and retained paths and the safe retry action are reported
- **AND** retry after the failure is removed succeeds without an implicit upgrade or destructive cleanup

### Requirement: WNS-03 Native executable selection and owned activation
Windows bootstrap/runtime services SHALL resolve native `.exe` entry points and virtual-environment `Scripts` paths in user-local locations, respecting explicit bootstrap-location overrides and spaces/Unicode. Source setup SHALL preserve an existing working shared selection unless explicit publication is requested or no working selection exists, and SHALL report both selected and newly prepared provenance. Persistent PowerShell activation SHALL be previewed and modify only an unmodified owned section; authored profile content, unrelated executables, machine PATH and execution policy SHALL be preserved.

#### Scenario: A second checkout is prepared
- **WHEN** source bootstrap runs in a different Windows checkout while a working shared engine is selected
- **THEN** it prepares that checkout's environment and prints its direct executable/provenance while preserving the shared selection
- **AND** explicit alias publication subsequently selects the verified new environment

#### Scenario: Activation survives a fresh terminal
- **WHEN** an approved owned activation section is applied under a home/install path containing spaces and Unicode and a fresh native terminal opens
- **THEN** `ai-dlc` and the pinned runtime tools resolve to the intended native paths without duplicate PATH entries

#### Scenario: The profile has authored changes or policy blocks activation
- **WHEN** an owned section is modified, a profile is redirected, or policy prevents profile execution
- **THEN** activation refuses the unsafe change and names the conflict/policy plus the usable direct executable route without overwriting authored bytes

### Requirement: WNS-04 Provision only the supported selected subset
Windows machine planning/apply SHALL support selected core Git/GitHub CLI and pinned Python/uv runtimes with the bootstrap's verified mise prerequisite. It SHALL preview exact native package identity, preserve adequate installed tools without opportunistic upgrades, and report observed versions. Missing/disallowed package managers SHALL produce named native recovery guidance without automatic elevation. Unsupported known modules SHALL be individually identified; unselected optional modules SHALL NOT block the minimal journey, while unmet selected or component-required modules SHALL prevent complete readiness. Authentication and installed-client recognition SHALL remain separate statuses.

#### Scenario: A minimal profile selects core and Python
- **WHEN** native setup resolves only core/Python and their project requirements
- **THEN** it plans/prepares only their supported native prerequisites, verifies executable/version readback and does not install unrelated catalog modules or log in to accounts

#### Scenario: A selected optional tool lacks a Windows recipe
- **WHEN** a selected or implied module is known but unsupported on Windows
- **THEN** the result names that module, required role and manual/unsupported disposition and cannot claim full readiness
- **AND** an unsupported module that was never selected is not a reason to force WSL

#### Scenario: Native package installation cannot proceed
- **WHEN** winget is unavailable, package/version resolution fails or policy denies a required user-scope install
- **THEN** the plan/apply result remains incomplete with the precise prerequisite and native recovery steps
- **AND** rerun after policy-approved manual installation verifies the tool without requesting an unrelated upgrade

### Requirement: WNS-05 Native generic and Python project behavior
New generic management commands and initialized Python setup/check commands SHALL use the portable command contract and run on Windows and supported Unix platforms. Python initialization SHALL preserve separate syntax and behavioral checks and their missing/empty/all-skipped failure behavior. Checks SHALL install nothing. Noninitializing adoption SHALL preserve authored configuration, commands, tests and existing dependency locks; it SHALL NOT silently convert POSIX scripts or substitute the engine repository's contributor workflow. Repeated setup/render/update SHALL preserve pinned source identity and authored managed-file conflict behavior.

#### Scenario: The initialized Python application's behavior regresses
- **WHEN** a native initialized Python project is prepared and its output changes while syntax remains valid
- **THEN** the ordinary required application test fails, and restoring behavior returns the check to passing without network installation during checks

#### Scenario: Existing generic or Python work is adopted
- **WHEN** native adoption targets a repository with authored commands, tests and dependency locks
- **THEN** those artifacts remain unchanged, the team's acceptance check runs through the normal service, and any explicit POSIX requirement is named without translation

#### Scenario: Setup or managed content needs recovery
- **WHEN** a Python environment is removed, noninitializing adoption lacks its required lock, or a generated file contains an authored edit
- **THEN** setup reruns the needed verified work or reports the missing lock/conflict without re-resolving dependencies or overwriting the authored edit

### Requirement: WNS-06 Windows CI and consumer assets have native evidence
The verification/release-consumer workflows SHALL include actual Windows native bootstrap/service execution and generic/Python passing/failing checks without POSIX helpers. They SHALL preserve existing Unix jobs and exact revision/configuration/artifact bindings. Candidate verification SHALL test built verified assets without publishing; existing-release replay SHALL be read-only and SHALL exercise a minimal seed and generated project against unchanged published assets. A Windows Server runner SHALL NOT be reported as Windows 11 desktop qualification.

#### Scenario: A candidate is verified natively
- **WHEN** a candidate wheel, hashed constraints and manifest are tested on the Windows runner
- **THEN** both minimal seed and generated project bootstrap from those assets, native required receipts bind their identities, behavioral regression fails as expected, and no package/tag/release is published

#### Scenario: Published assets are replayed
- **WHEN** maintainers request Windows verification of an existing published tag
- **THEN** the workflow preserves the assets/tag and records original asset identity separately from replay workflow revision and actual Windows outcomes

#### Scenario: A platform test is skipped or fails
- **WHEN** a required Windows safety/consumer case is skipped, fails or does not run
- **THEN** the result cannot be counted as successful Windows qualification even when Linux/macOS jobs pass

### Requirement: WNS-07 Clean Windows 11 qualification is observed
Windows 11 x64 support claims SHALL require a recorded clean-account native PowerShell walkthrough of install, selected preparation, generic/Python project adoption/init, rendering and meaningful passing/failing acceptance checks. Evidence SHALL identify OS, shell, architecture, filesystem, engine source/release identity, selected profile/source revisions, tools and outcomes. It SHALL exercise spaces/Unicode, repeat setup, fresh terminal, concurrent writes, edited managed content, interrupted/blocked publication and recovery. Absent desktop-client recognition/authentication evidence SHALL remain not-assessed.

#### Scenario: The clean consumer walkthrough succeeds
- **WHEN** the full matrix runs on a clean Windows 11 x64 account without WSL/POSIX helpers
- **THEN** qualification records the actual identity and positive/negative/recovery results, remaining limits and the observed time/manual steps rather than invented savings

#### Scenario: Only hosted CI or an unverified client is available
- **WHEN** Windows Server CI passes but no Windows 11 walkthrough or installed-client smoke evidence exists
- **THEN** the record states exactly which obligations remain open and does not claim successful Windows 11 desktop-client adoption

### Requirement: WNS-08 Native documentation and packaged assets stay aligned
Canonical setup/release guidance and packaged/source project bootstrap assets SHALL agree on supported platforms, native commands, consumer versus contributor purpose, optional WSL status and qualification limits. Documentation dispositions SHALL be content-bound to reviewed targets. Downstream guidance SHALL remain generic and SHALL NOT embed the AI-DLC repository's personal tracker, accounts or machine paths.

#### Scenario: A consumer follows native setup guidance
- **WHEN** a teammate follows README and generated-project instructions for Windows
- **THEN** they reach the native selected-project path with explicit supported subset and source/release identity, rather than an implicit engine-contributor or mandatory WSL route

#### Scenario: A source/template or claim drifts
- **WHEN** native bootstrap assets diverge between source and packaged templates or documentation claims unobserved qualification
- **THEN** required parity/documentation review fails and the mismatch is corrected before delivery is accepted
