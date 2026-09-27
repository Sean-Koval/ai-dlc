## ADDED Requirements

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
