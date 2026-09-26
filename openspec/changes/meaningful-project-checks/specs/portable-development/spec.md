## ADDED Requirements

### Requirement: PC-01 Explicit focused project checks

The project-check service and CLI SHALL allow an explicit nonempty ordered list
of existing `[checks.commands]` IDs; the CLI SHALL accept repeated `--check ID`.
Explicit IDs SHALL select exactly those commands, independently of membership in
`checks.required`. Explicit selection combined with all-command mode
(`--no-required` / `required_only=False`) SHALL be rejected as ambiguous; the
default/explicit required-only flag SHALL remain compatible with selected optional
IDs because it filters only when IDs are omitted. Omitting selection SHALL retain
existing required-only/all-command behavior. The service
SHALL reject empty lists, blank, unknown or duplicate IDs, and missing/empty/nonstring
selected commands before runtime resolution or command execution. Invalid
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
