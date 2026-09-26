## MODIFIED Requirements

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
