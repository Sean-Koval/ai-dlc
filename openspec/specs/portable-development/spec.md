# portable-development Specification

## Purpose
TBD - created by archiving change portable-development-v4. Update Purpose after archive.
## Requirements
### Requirement: Project environment and checks are repository-owned
The system SHALL prepare declared runtimes and ordered dependency steps and execute
required checks from one repository manifest. Machine settings SHALL NOT weaken checks.

#### Scenario: An interrupted setup is retried
- **WHEN** a dependency step fails after earlier steps succeeded
- **THEN** a retry verifies completed steps and resumes remaining work

#### Scenario: A check does not run successfully
- **WHEN** a required check is missing, cancelled, skipped or fails
- **THEN** its receipt SHALL NOT qualify as successful completion evidence

### Requirement: Completion uses trusted merged-revision evidence
The system SHALL verify the configured repository, target branch, workflow, merged
revision, configuration digests and required outcomes before completing a tracker item.

#### Scenario: An unrelated green workflow exists
- **WHEN** the workflow identity or checked revision differs
- **THEN** work completion is blocked with the failing gate identified

#### Scenario: Completion succeeds but handoff writing fails
- **WHEN** the tracker is closed and knowledge storage is unavailable
- **THEN** report completed with handoff pending and retry only the missing note

### Requirement: Configuration and content remain portable
The system SHALL separate base, personal, project and machine scopes, preserve existing
content during adoption/update, and verify provider and skill artifacts before loading.

#### Scenario: Generated content and user content both changed
- **WHEN** applying the update would overwrite an authored change
- **THEN** report the conflict without overwriting the destination

#### Scenario: A provider binding changes
- **WHEN** new work selects a different provider
- **THEN** existing records retain their bindings until explicitly mapped by rebind

### Requirement: Execution limitations are explicit
The system SHALL refuse unsupported required policies and unavailable provider-test
isolation. Local fixture tests SHALL NOT be represented as live platform verification.

#### Scenario: Docker is unavailable
- **WHEN** provider conformance testing is requested
- **THEN** report unavailable and do not execute the provider on the host

#### Scenario: Offline tracker conformance follows delivered adapters
- **WHEN** a packaged offline GitHub Issues, Jira Cloud, or Plane target is selected
- **THEN** it runs the existing real adapter transport and shared lifecycle fixtures,
  including GitHub Projects behavior and the required packaged test helpers
- **AND** provider and all aggregates include those fixtures without duplicate paths
- **AND** missing fixtures fail explicitly and results remain offline-only; selecting
  an unavailable live scope cannot inherit offline success

### Requirement: Release bootstrap candidates bind verified artifacts
Candidate release manifests SHALL bind one engine wheel and hashed dependency constraints
by their actual SHA256 digests and an explicit HTTPS artifact base URL. Candidate generation
SHALL validate engine identity/version and SHALL NOT publish assets or overwrite an existing
manifest. Bootstrap SHALL reject corrupted downloads before installing the engine.

#### Scenario: A maintainer prepares candidate assets
- **WHEN** the wheel identity matches the requested engine version and constraints exist
- **THEN** generate a shell-safe manifest of exact filenames, HTTPS URLs and artifact hashes
- **AND** retain publication and live installation as separate verification obligations

#### Scenario: A candidate is ambiguous or stale
- **WHEN** multiple wheels, a mismatched wheel version or an existing output is supplied
- **THEN** refuse generation without replacing the existing manifest

#### Scenario: A release download is corrupted
- **WHEN** the wheel or constraints differ from the manifest digest
- **THEN** refuse engine installation and preserve the previously selected CLI

### Requirement: PC-01 Explicit focused project checks

The project-check service and CLI SHALL allow an explicit nonempty ordered list
of existing `[checks.commands]` IDs; the CLI SHALL accept repeated `--check ID`.
Explicit IDs SHALL select exactly those commands, independently of membership in
`checks.required`. Explicit selection combined with all-command mode
(`--no-required` / `required_only=False`) SHALL be rejected as ambiguous; the
default/explicit required-only flag SHALL remain compatible with selected optional
IDs because it filters only when IDs are omitted. Omitting selection SHALL retain
existing required-only/all-command behavior. The service
SHALL reject empty lists, blank, unknown or duplicate IDs, and missing/empty/malformed
selected commands under the portable command contract (a legacy POSIX string,
a native argv record, or an explicit posix/powershell script record) before runtime resolution or command execution. Invalid
selection SHALL fail concisely and SHALL NOT write a new execution receipt.

#### Scenario: A developer selects one required and one optional check
- **GIVEN** required checks `lint` and `test` and optional command `smoke`
- **WHEN** project check receives `--check smoke --check lint`
- **THEN** only smoke and lint execute in that order
- **AND** the CLI succeeds if both selected commands pass with exit zero
- **AND** receipt required IDs remain lint and test and outcomes contain only smoke and lint

#### Scenario: Selection is malformed
- **WHEN** an explicit selection is empty, combined with all-command mode, includes a blank/unknown/duplicate ID, or selects an invalid command
- **THEN** validation fails before runtime resolution or any command executes
- **AND** no new execution receipt is written

#### Scenario: A selected command fails or is cancelled
- **WHEN** a selected command fails, times out or is interrupted, including an optional check
- **THEN** the CLI exits nonzero and outcomes accurately record the failure or cancellation

#### Scenario: No selection is supplied
- **WHEN** project check runs without `--check`
- **THEN** its existing required-only default and all-command option remain unchanged

#### Scenario: A selected command uses the native command contract
- **WHEN** an explicit check ID selects a valid argv or explicit-shell record
- **THEN** validation accepts that record and executes it through the shared command service in selected order
- **AND** malformed records fail before runtime resolution or any new execution receipt

### Requirement: PC-02 Focused checks do not weaken completion evidence

Focused receipts SHALL retain full manifest required IDs, configuration/environment
digests and existing revision, target and dirty-state bindings. Completion SHALL
continue to require exactly all configured required checks passing under existing
trusted merged-revision rules. Focused guidance SHALL distinguish edit feedback
from the full required run immediately before merge after target-branch integration.

#### Scenario: A partial run passes
- **GIVEN** the manifest requires lint and test
- **WHEN** a successful selected lint receipt is submitted as completion evidence
- **THEN** existing completion validation rejects the missing test outcome even if other trusted fields match

#### Scenario: A selected run covers the complete required set
- **WHEN** selected outcomes exactly cover all required IDs and pass
- **THEN** completion validation applies its unchanged revision, configuration, target and clean-state requirements
- **AND** the selector itself neither bypasses those requirements nor prohibits otherwise valid evidence

### Requirement: PC-03 New Python starters exercise observable behavior

New Python initialization SHALL retain a separately named syntax check and add a
required `application-tests` command using the Python standard library. Its
starter test SHALL exercise the generated application's `Hello, world!` output.
The generated runner SHALL discover additional `test*.py` tests under `tests`,
fail on test/import errors, and fail if discovery is missing/empty or every test
is skipped. Checks SHALL install nothing and SHALL NOT dirty tracked content.
Non-initializing adoption SHALL NOT add starter tests or replace authored commands,
required IDs, application manifests or existing tests; other language presets
SHALL NOT receive these Python starter assets.

#### Scenario: A valid Python starter is checked offline
- **WHEN** the initialized starter runs its syntax and application tests after preparation without network access
- **THEN** both checks succeed and tracked content remains unchanged

#### Scenario: Output regresses without a syntax error
- **WHEN** the starter prints incorrect output with otherwise valid Python syntax
- **THEN** syntax validation may pass but application-tests fails

#### Scenario: A test suite is empty or entirely skipped
- **WHEN** no runnable tests remain because discovery is missing, empty or all discovered tests skip
- **THEN** application-tests exits nonzero with an actionable explanation

#### Scenario: A team adds another behavioral test
- **WHEN** a new test matching unittest discovery fails
- **THEN** application-tests discovers it and exits nonzero

#### Scenario: An existing project chooses its own test tools
- **WHEN** adoption is applied without initialization to a project with authored checks and tests
- **THEN** existing preservation/conflict behavior protects that content
- **AND** the Python starter runner and test are not generated and no universal test framework is imposed

### Requirement: BCO-01 Inspect existing behavioral verification before proposing commands

Behavioral-check onboarding guidance SHALL inspect the target project's existing setup steps, declared checks, test configuration, CI commands and relevant observable acceptance before recommending commands. It SHALL identify the sources inspected, unknowns and a proposed mapping from one concrete requirement to an existing or explicitly proposed behavioral check. It SHALL NOT infer test adequacy from filenames, syntax checks or a successful setup alone, and SHALL NOT impose a universal test framework.

#### Scenario: Existing team tests are available
- **WHEN** onboarding finds an authored test command and a requirement it exercises
- **THEN** it proposes reusing that command, identifies its source and requirement mapping, and preserves authored tests and unrelated checks

#### Scenario: No behavioral check is evident
- **WHEN** inspection finds only syntax checks or cannot establish what behavior a command verifies
- **THEN** it reports that uncertainty and asks for a reviewed requirement/check choice without describing the project as behaviorally verified

### Requirement: BCO-02 Reviewed commands use existing setup and check services

Onboarding SHALL present explicit proposed setup prerequisites, check IDs, commands and required-versus-optional selections for review before shared configuration changes. Accepted commands SHALL use existing repository-owned setup and project-check services and the project's supported execution contract. Running a check SHALL NOT implicitly install tools, replace authored tests, or select a different shell to make an incompatible command pass.

#### Scenario: A maintainer accepts a team command
- **WHEN** a reviewed behavioral command is added to the manifest
- **THEN** it runs through `ai-dlc project check --check CHECK_ID` and participates in `--required` only when deliberately selected as required

#### Scenario: Proposed setup has not been accepted
- **WHEN** inspection identifies a missing dependency but setup changes have not been reviewed
- **THEN** guidance names the prerequisite and existing setup action without installing it or presenting readiness as success

### Requirement: BCO-03 Normal check runtime is a visible prerequisite

Behavioral onboarding SHALL identify and verify the normal runner's mise prerequisite even for generic projects with an empty tools table, using existing runtime resolution and actionable unavailable-runtime behavior. It SHALL NOT replace a failed normal-runner invocation with direct shell execution as equivalent evidence. Evaluation preparation SHALL provide the required common check runtime in both comparison arms before a candidate ordinary required-check smoke, without invoking a model service or claiming completion of the deferred paid comparison.

#### Scenario: Generic project lacks mise
- **WHEN** the selected runtime is absent from PATH and the bootstrap runtime location
- **THEN** no check runs, the existing structured runtime-unavailable result names the remedy, and no passing receipt or successful onboarding claim is produced

#### Scenario: Candidate preparation verifies the declared runner
- **WHEN** a comparison base and candidate are prepared with their declared common runtime
- **THEN** an offline candidate smoke executes `ai-dlc project check --required` and retains its actual result, while paid comparison, live billing and human quality findings remain pending

### Requirement: BCO-04 Demonstrate a behavioral regression only in isolated evidence

The onboarding workflow SHALL guide a passing, deliberately failing and restored-passing rehearsal of one reviewed requirement using its selected check in an explicitly isolated disposable fixture. It SHALL verify isolation and retain fixture/source identity, the introduced regression and the three observed outcomes. It SHALL NOT alter the active project worktree to manufacture a failure, reset user changes, use production data or mutate remote services for the rehearsal. Unavailable isolation or an unobserved expected failure SHALL remain visible as incomplete evidence.

#### Scenario: Check catches a meaningful regression
- **WHEN** a reviewed fixture initially passes, a deliberate behavior regression makes its check fail, and restoring the fixture passes again
- **THEN** evidence identifies that requirement, command, fixture and all three observed outcomes without claiming complete product quality

#### Scenario: Regression is not detected
- **WHEN** the deliberately changed behavior still passes the selected check
- **THEN** the workflow reports that the rehearsal did not demonstrate regression detection and does not label it successful

#### Scenario: Isolation cannot be established
- **WHEN** the proposed fixture resolves into the active checkout or would access production data or remote mutations
- **THEN** the rehearsal stops before introducing the regression and leaves user content unchanged

### Requirement: BCO-05 Evidence preserves focused and full-check distinctions

Behavioral onboarding SHALL retain existing focused and full required-check receipt semantics, including exact revision, configuration, environment, target and dirty-state bindings. Evidence SHALL distinguish observed requirement behavior from unassessed adequacy, human quality judgment and productivity. Guidance SHALL use concise task-specific links rather than place a complete testing protocol in every session's shared rules.

#### Scenario: Focused behavioral feedback passes
- **WHEN** only one of several required checks passes in a focused run
- **THEN** that feedback can be reported, but its partial receipt cannot satisfy completion and guidance still names the full required run

#### Scenario: A rehearsal is complete
- **WHEN** the three fixture outcomes are recorded successfully
- **THEN** the result claims only demonstrated detection for the selected behavior and identifies remaining native-platform, human-quality and comparison evidence as unassessed

