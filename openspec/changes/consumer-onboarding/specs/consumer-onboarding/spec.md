## ADDED Requirements

### Requirement: CO-01 Distinct consumer and contributor routes
Consumer guidance SHALL distinguish engine installation, explicit profile enrollment and target-project adoption from contribution to AI-DLC itself. It SHALL route consumer checks to the selected target project and SHALL NOT require AI-DLC's contributor full checks or inherit the engine repository's tracker, vault, providers or client selections.

#### Scenario: Consumer cloned the engine for installation
- **WHEN** a teammate uses a source checkout to install the engine for a different repository
- **THEN** guidance identifies the target repository explicitly and recommends that project's setup and selected meaningful check, reserving engine full checks for engine contribution

#### Scenario: Released engine lacks a requested feature
- **WHEN** documented selected onboarding features postdate the installed release
- **THEN** the route names the version/source limitation and requests an explicit reviewed installation choice rather than implying equal capability from a shared version string

### Requirement: CO-02 Non-mutating explicit preflight
`project onboard --root PATH` SHALL require an explicit existing readable target directory without a current-directory default and SHALL produce a schema-versioned ordered plan from the target configuration and explicit selections, report OS/architecture/shell/client support, and expose no apply mode. It SHALL inspect only local metadata and read-only resolvers; source fetches, subprocess execution, configuration writes and credential values SHALL be excluded.

#### Scenario: Target is missing or unreadable
- **WHEN** root is omitted, nonexistent, unreadable or resolves only to the engine checkout for a consumer request
- **THEN** preflight reports the target-selection problem without creating a directory or defaulting to the engine configuration

#### Scenario: Self-contained target is already adopted
- **WHEN** the target supplies its client and project configuration and the user has not selected enrollment
- **THEN** the plan uses those project choices, identifies enrollment as unselected and writes or executes nothing

#### Scenario: Required selection is incomplete
- **WHEN** source/ref/profile selection is partial, a fresh project's client is absent, or explicit input conflicts with target configuration
- **THEN** the plan reports the specific missing input or conflict with exit 1 and emits no runnable action containing invented values

### Requirement: CO-03 Bounded delegation and truthful progress
The onboarding plan SHALL order exact available existing operations for reviewed enrollment, machine planning, adoption, setup, rendering, readiness and the target check. Each action SHALL declare argument-array identity, dependencies, expected effects and review requirements. Exit 0 SHALL mean actionable planning only; installation, rendering, offline readiness and native recognition/authentication SHALL remain distinct.

#### Scenario: Ready to preview adoption
- **WHEN** prerequisites and explicit target choices are known
- **THEN** the plan recommends the existing adoption preview followed by a separately reviewed apply operation and keeps native qualification not-assessed

#### Scenario: Fresh target has selected enrollment
- **WHEN** a fresh target selects a complete reviewed profile and client
- **THEN** the ordered plan makes target adoption a prerequisite of root-scoped machine planning, so the machine owner receives an existing target configuration rather than falling back to another repository

#### Scenario: Existing owned guidance is edited
- **WHEN** a read-only inspection identifies an ownership conflict
- **THEN** the plan reports the existing conflict resolution route and does not overwrite, execute recovery or bypass the owning service

### Requirement: CO-04 Honest unsupported-platform routing
Consumer entry documentation and preflight SHALL identify supported platform/shell/client combinations and scoped unsupported components before recommending execution. This capability SHALL be deliverable on supported Unix platforms while native Windows remains unsupported. It SHALL NOT silently prescribe WSL, Linux containers or translated shell commands.

#### Scenario: Windows cannot load the current engine
- **WHEN** a Windows teammate opens the consumer installation instructions before engine startup
- **THEN** the instructions identify current native Windows limits without requiring successful CLI import and without presenting POSIX bootstrap as a native Windows route

#### Scenario: Unknown or optional component support
- **WHEN** the shell is unknown or an optional selected component lacks platform support
- **THEN** the plan names the uncertainty or component, distinguishes optional from core blockers and omits unsupported executable recommendations

### Requirement: CO-05 Repeatability and observable onboarding evidence
Rerunning onboarding SHALL derive its plan from current local state without a persisted orchestration session. Verification SHALL cover preservation, no side effects and one real supported-platform target-project route; unsupported-platform fixture tests SHALL NOT establish native qualification.

#### Scenario: A user completes one recommended operation
- **WHEN** preflight is rerun after that explicit operation
- **THEN** it reflects the new observed stage without replaying operations or claiming later stages completed

#### Scenario: Target check cannot run
- **WHEN** target runtime or check configuration is missing
- **THEN** the route gives the specific next action, reports no passing check and retains native qualification not-assessed
