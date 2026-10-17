# session-learnings Specification

## Purpose
TBD - created by archiving change session-learnings. Update Purpose after archive.

## Requirements

### Requirement: SL-01 Learning storage is idempotent and optional
`work finish` SHALL accept an optional learning note and store it at `learnings/<YYYY-MM-DD>-<work-id>.md` through the knowledge provider's `note` operation under a journaled operation identity, so a retried finish stores the note exactly once. The stored note SHALL carry knowledge-note frontmatter that validates against `contracts/knowledge-note.schema.json`: a body without frontmatter gets generated frontmatter, and a body with frontmatter keeps every supplied field while only missing fields are added. Generated `sources` SHALL include the merged pull request URL and merge commit that the finish gate verified. `author` SHALL come from `AI_DLC_AUTHOR` when set, otherwise the CLI user's GitHub login, and SHALL NOT be inferred from another session. The journal SHALL keep the final note so a retry writes byte-identical content, and reusing the operation with a different body SHALL report a conflict. Finishing without a learning SHALL still complete and SHALL report a one-line reminder. A knowledge provider failure or invalid frontmatter SHALL leave the tracker completion intact and report the note as pending.

#### Scenario: A finish with a learning is retried
- **WHEN** `work finish` runs twice with the same learning body after the first run stored the note
- **THEN** the vault holds one byte-identical note at the learning path with one operation marker and the second run reports the recorded result without writing again

#### Scenario: A learning has no frontmatter
- **WHEN** `work finish` stores a learning body without frontmatter
- **THEN** the note's generated frontmatter validates against the schema and contains the merged PR URL and merge commit

#### Scenario: A learning supplies some fields
- **WHEN** the learning's frontmatter sets `confidence: high` and `scope: project`
- **THEN** the stored note keeps those values and adds only the missing fields

#### Scenario: A different body reuses the operation
- **WHEN** a later finish supplies a different learning body for the same work
- **THEN** the result reports a conflict and the stored note is unchanged

#### Scenario: A finish has no learning
- **WHEN** `work finish` runs without a learning
- **THEN** completion proceeds unchanged and the result carries a one-line reminder to record a learning

#### Scenario: The knowledge provider is unavailable
- **WHEN** the vault is unconfigured or the note write fails
- **THEN** the tracker is closed once, the result reports the learning as pending with the reason, and a later finish can store it

### Requirement: SL-02 Recall is read-only and bounded
`work start` and the `session-start` hook SHALL recall at most five stored learning notes whose path or body matches the work record's title words or the final segment of its specification artifact, reporting each note's vault path and first content line. For notes with knowledge-note frontmatter, recall SHALL skip notes whose `valid_to` has passed and SHALL also report `kind`, `author`, `review_by` and `stale` (true when `review_by` has passed); the session hook SHALL prefix stale notes with `(stale)`. Notes without frontmatter SHALL recall as before. Recall SHALL read only notes under `learnings/`, SHALL write nothing, and SHALL produce nothing without failing when no vault is configured, the vault is absent, or nothing matches.

#### Scenario: A stored learning matches the record title
- **WHEN** `work start` runs for a record whose title contains a word found in a stored learning note
- **THEN** the result lists that note's path and first content line and the vault is unchanged

#### Scenario: A learning has expired or is due for review
- **WHEN** one matching note's `valid_to` has passed and another's `review_by` has passed
- **THEN** the first is not listed and the second is listed with `stale: true`

#### Scenario: No vault is configured
- **WHEN** `work start` or the `session-start` hook runs in a project without a configured or existing vault
- **THEN** no learning is listed and the command completes as before

#### Scenario: Many notes match
- **WHEN** more than five learning notes match the record
- **THEN** at most five are listed

### Requirement: SL-03 Friction counting is local and never transmitted
The hook SHALL count, per session, its own denials, repeated identical commands and blocked or failed `work` results from the payloads it receives, in a file under `.ai-dlc/local/session/`. The `stop` event SHALL add a learning-note reminder only when the session count has reached three. The counter SHALL never be sent anywhere or written outside `.ai-dlc/local/`.

#### Scenario: A session stays below the threshold
- **WHEN** a session records two friction events and then stops
- **THEN** the stop response carries no friction reminder

#### Scenario: A session reaches the threshold
- **WHEN** a session records three friction events and then stops
- **THEN** the stop response carries a friction reminder naming the count and the `knowledge note learnings/...` command

#### Scenario: The counter is local
- **WHEN** friction is recorded
- **THEN** the only write is the session file under `.ai-dlc/local/session/` and no network call is made

### Requirement: SL-04 Learning frontmatter can be checked
`ai-dlc knowledge check --vault PATH` SHALL read the notes under `learnings/` without writing, report each note whose knowledge-note frontmatter fails the schema, list notes without frontmatter or with pre-schema frontmatter as legacy, and exit 1 when any note is invalid and 0 otherwise.

#### Scenario: A vault has an invalid learning
- **WHEN** a learning's frontmatter fails the schema
- **THEN** `knowledge check` names it and exits 1

#### Scenario: A vault is valid
- **WHEN** every learning with frontmatter validates
- **THEN** `knowledge check` exits 0 and the vault is unchanged
