## ADDED Requirements

### Requirement: TB-01 GitHub Issues is the default tracker
The packaged base profile, `project init`, `project adopt` and the Copier template SHALL select the `github-issues` tracker when no tracker is chosen, and SHALL NOT render a Linear provider, module or `LINEAR_API_KEY` reference. A project's own tracker selection and recorded Copier answers SHALL continue to win over these defaults.

#### Scenario: A new project accepts defaults
- **WHEN** `ai-dlc project init` runs with the generic preset and no provider options
- **THEN** the generated `ai-dlc.toml` selects `tracker = "github-issues"` and no generated file mentions `LINEAR_API_KEY`

#### Scenario: Finished history stays valid after the Linear configuration is removed
- **WHEN** finished work records pinned to `tracker = "linear"` remain and the project has no `[providers.linear]` table
- **THEN** `ai-dlc work validate --all` passes because finished records keep their historical fingerprints

### Requirement: TB-02 Removed adapters refuse with guidance
A provider whose resolved kind is `linear` SHALL be refused with a typed refusal (exit status 2) before any credential use, remote request or write. The message SHALL name `github-issues` and `jira-cloud` and the earlier-release `project tracker-migrate` path. Lifecycle commands, provider connection, scaffolding and rebinding to the removed kind SHALL all refuse; doctor SHALL report it as a configuration gap.

#### Scenario: Work start on a Linear-bound record
- **WHEN** a reviewed record whose tracker resolves to `linear` is started
- **THEN** the command exits with status 2 and the removal message, and the record, branch and tracker are unchanged

### Requirement: TB-03 Unsupported adapters require an explicit opt-in
A shipped adapter marked unsupported SHALL NOT be scaffolded by `project init` or `project adopt` unless `--allow-unsupported` is passed. Recorded Copier answers that already select it SHALL remain valid for `project sync`. Doctor SHALL report each selected unsupported adapter as `unsupported, unqualified`. Plane SHALL be marked unsupported.

#### Scenario: Plane is selected without the opt-in
- **WHEN** `project init --tracker plane` runs without `--allow-unsupported`
- **THEN** it refuses before staging and names the flag
- **WHEN** the same command passes `--allow-unsupported`
- **THEN** the Plane tracker is scaffolded as before

### Requirement: TB-04 Finish-only tracker writes
The project or base configuration MAY set `[work] tracker_writes` to `lifecycle` (the default) or `finish-only`; other values and other `work` fields SHALL be refused, and personal or machine layers SHALL NOT set it. Under `finish-only`, `work start` SHALL bind the branch and MAY read the linked ticket, but SHALL NOT publish, transition or comment on it; `work finish` SHALL keep closing the ticket after its gates. A finish whose ticket is already closed SHALL reconcile the closed state rather than fail.

#### Scenario: A repository also uses hangar intake
- **WHEN** `[work] tracker_writes = "finish-only"` is configured and reviewed work is started
- **THEN** the tracker records no create, transition or comment request and the result reports the skipped transition

#### Scenario: Hangar already closed the ticket
- **WHEN** `work finish` runs for merged work whose ticket is already closed
- **THEN** finish reports the reconciled closed state and completes without a duplicate transition
