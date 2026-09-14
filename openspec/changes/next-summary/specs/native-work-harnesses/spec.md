## ADDED Requirements

### Requirement: NH-05 Offline next-step summary

`ai-dlc next` SHALL derive each work record's lifecycle state from its local artifacts alone and print a plain-text summary naming the state and the next command per record, the required checks and the check command, and stating that the tracker was not consulted. A record without a `tracker` artifact is `unpublished`; with a tracker and no `pr` it is `in progress`; with a `pr` and a specification under `openspec/changes/` outside `openspec/changes/archive/` it is `awaiting merge, archive first`; with a `pr` and an archived specification, or no required specification, it is `awaiting merge`. Unpublished records SHALL appear only with `--all`. `--json` SHALL return the same records as `id`, `state`, `tracker`, `pr` and `next` with a `status` string. `ai-dlc context --brief` SHALL print the same text, `ai-dlc context` SHALL keep its machine-readable output, and the session-start hook SHALL include the first ten lines of the summary.

#### Scenario: A record has no tracker artifact
- **WHEN** the summary reads a record whose artifacts have no `tracker`
- **THEN** the record is `unpublished` with `next: ai-dlc work publish <id>`, and it is printed only with `--all`

#### Scenario: A record is published but has no pull request
- **WHEN** a record has a `tracker` artifact and no `pr` artifact
- **THEN** the record is `in progress` with `next: ai-dlc work pr <id>`

#### Scenario: A pull request exists and the change is not archived
- **WHEN** a record has a `pr` artifact and its `spec` is under `openspec/changes/` but not under `openspec/changes/archive/`
- **THEN** the record is `awaiting merge, archive first` with the archive command as its next step

#### Scenario: A pull request exists and the change is archived
- **WHEN** a record has a `pr` artifact and its `spec` is archived or `requires_spec` is false
- **THEN** the record is `awaiting merge` with `next: ai-dlc work finish <id>`, and the header states that the tracker was not consulted rather than guessing whether the record is finished

#### Scenario: The summary makes no remote calls
- **WHEN** `ai-dlc next` runs with an empty `PATH` and no network
- **THEN** it exits 0 in under one second, reads only the repository tree, and its JSON form carries a `status` string

#### Scenario: A session starts
- **WHEN** the session-start hook runs in a project whose records can be read
- **THEN** the returned context contains the first ten lines of the summary, and when the project cannot be read the context falls back to the plain instruction
