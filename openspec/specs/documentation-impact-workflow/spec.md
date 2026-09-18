# documentation-impact-workflow Specification

## Purpose
Require revision-bound documentation impact dispositions.

## Requirements

### Requirement: DI-01 Scoped impact inspection
A shared CLI and MCP service SHALL inspect a Git comparison plus current working content, match optional catalog code, requirement and verification references, and expose changed unmapped files. Reads SHALL stay inside the repository. The CLI SHALL expose the documentation workflow under one `ai-dlc docs` group whose commands are exactly `check`, `review`, `gate`, `read`, `search` and `init`; impact inspection, disposition recording, baseline proposal, review-packet preparation and review validation SHALL be modes of `ai-dlc docs review`. Each former `ai-dlc project docs-*` command SHALL keep working for one release as a hidden alias that runs the same service, keeps its stdout and exit status, and prints one deprecation line naming its replacement to stderr.

#### Scenario: Scoped impact inspection
- **WHEN** a mapped public interface changes
- **THEN** the matching document requires review and unmapped changes remain visible

#### Scenario: The documentation group lists its commands
- **WHEN** a user runs `ai-dlc docs --help`
- **THEN** exactly `check`, `review`, `gate`, `read`, `search` and `init` are listed and no empty command group is registered

#### Scenario: Legacy command names keep working with a deprecation notice
- **WHEN** a caller runs a former `ai-dlc project docs-*` command
- **THEN** the same service runs with the same stdout and exit status, the name is absent from the command list in `ai-dlc project --help`, and one deprecation line naming the `ai-dlc docs` replacement is printed to stderr

#### Scenario: A review mode is given incomplete options
- **WHEN** `ai-dlc docs review` is run with a mode flag whose required options are missing, with two modes at once, or with a mode-specific option and no mode
- **THEN** the CLI reports a usage error and runs no service

### Requirement: DI-03 Prevent new objective debt
Documentation checks SHALL be project-selectable, compare current objective findings against an explicit historical baseline, and refuse new defects without blocking solely on unchanged accepted historical findings. AI-DLC SHALL enroll after recording its baseline.

#### Scenario: Prevent new objective debt
- **WHEN** an unrelated historical finding remains while a new broken link is introduced
- **THEN** the new defect blocks and historical debt remains separately visible

### Requirement: DI-02 Content-bound dispositions
Documentation dispositions SHALL identify updated, reviewed-no-change or justified no-impact outcomes, each with a reason and reviewer, and SHALL bind each decision to the content of its target and of the sources mapped to that target, including that document's catalog entry. Evidence SHALL be stored per work item under `.ai-dlc/documentation/evidence/` so that concurrent branches do not write a shared path. Work records under `.ai-dlc/work/` SHALL be excluded from changed files, unmapped files and bound content unless a catalog mapping explicitly targets those paths; the work-records check validates their delivery state. The gate SHALL resolve its comparison independently of the evidence, SHALL compute changed files from the merge base of that comparison and `HEAD`, and SHALL require every impacted document and unmapped changed file to have a decision whose bound content equals current content. Missing decisions and stale decisions SHALL be reported separately, and a stale report SHALL name the paths whose content differs. Movement of the target branch that changes no bound content SHALL NOT invalidate a decision. Recording SHALL keep decisions that remain valid, SHALL refuse decisions for targets that are not required, and SHALL report kept, added, replaced and dropped targets. Schema 1 evidence at `.ai-dlc/documentation/current.json` SHALL keep passing under its recorded-base rules for one release when no per-work evidence exists.

#### Scenario: Bound content changes after disposition
- **WHEN** a target or one of its mapped sources changes after its decision is recorded
- **THEN** the gate reports that decision as stale and names the changed paths rather than accepting the earlier review

#### Scenario: Disjoint branches merge in either order
- **WHEN** two branches with disjoint changes each hold valid evidence and one merges before the other
- **THEN** the second branch updates from the target without a Git conflict in evidence storage, and its gate passes with no decision recorded again

#### Scenario: Target branch changes bound content
- **WHEN** the branch is updated from a target branch that changed a source bound by one of its decisions
- **THEN** the gate reports that decision as stale, names the source, and leaves the branch's other decisions valid

#### Scenario: Branch behind its target
- **WHEN** the comparison commit is not contained in `HEAD`
- **THEN** changed files are computed from the merge base, so target-branch changes the branch lacks are not reported as the branch's changes

#### Scenario: Push run on the target branch
- **WHEN** the gate runs on a merge commit with the replaced commit as its comparison
- **THEN** it requires valid decisions for what the merge introduced, and fails if conflict resolution altered bound content

#### Scenario: Catalog entry changes
- **WHEN** a document's catalog mapping changes after its decision while unrelated catalog entries also change
- **THEN** only that document's decision is stale

#### Scenario: Incremental recording
- **WHEN** new decisions are recorded for a work item whose evidence already holds decisions that remain valid
- **THEN** the valid decisions are kept, the new ones are added, decisions for targets no longer required are dropped, and the result lists each group

#### Scenario: A work record changes after dispositions are recorded
- **WHEN** a work record without an explicit catalog mapping changes after dispositions are recorded
- **THEN** the recorded documentation evidence still passes the gate

#### Scenario: A work record has an explicit catalog mapping
- **WHEN** an explicitly mapped work record changes
- **THEN** its mapped document requires review and its content remains bound to evidence

#### Scenario: Legacy evidence
- **WHEN** a project holds only schema 1 `current.json`
- **THEN** the gate applies the recorded-base rules, and the next recording writes per-work evidence and reports that `current.json` can be deleted
