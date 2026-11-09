## ADDED Requirements

### Requirement: KC-01 Capture notes name their origin

The knowledge-note schema SHALL accept the kinds `daily`, `meeting` and `thread`.
A note of those kinds SHALL name `origin` as `work` or `home`. A `meeting` or
`thread` SHALL name `source` with exactly one of `file` or `room` and a lowercase
hex `sha256`. `lane` SHALL be a tracker epic key. A `publish` block SHALL name a
bare-host `site` and a `space`, and SHALL record `page_id` and `version` together.
A note with `publish` SHALL name `origin`. Existing kinds SHALL NOT require
`origin`.

#### Scenario: A meeting without an origin
- **WHEN** a meeting note's frontmatter has no `origin`
- **THEN** validation reports that the note needs origin

#### Scenario: An existing learning
- **WHEN** a learning written before this change is validated
- **THEN** it validates without `origin`

### Requirement: KC-02 A source is captured once

`ai-dlc knowledge captured FILE --vault PATH` SHALL report the source's SHA-256,
computed after normalizing CRLF to LF, and every vault note whose `source.sha256`
equals it. It SHALL exit 1 when any note does, and write nothing.

#### Scenario: A transcript is captured twice
- **WHEN** a note already records the digest of the exported transcript
- **THEN** the command lists that note and exits 1

### Requirement: KC-03 Notes never cross the origin/site wall

Publication SHALL require `<vault>/.ai-dlc/publish.toml` naming `origin`, `site`
and `space`, with no default. `publish-plan` and `publish-record` SHALL refuse, and
write nothing, when the note's `origin` differs from the vault's, when its
`publish.site` differs from the vault's site, when its frontmatter is invalid, or
when it is a `daily` note.

#### Scenario: A work note in the home vault
- **WHEN** a note with `origin: work` is planned in a vault declaring `origin = "home"`
- **THEN** the plan is refused with an origin mismatch and the note is unchanged

#### Scenario: No declared target
- **WHEN** the vault has no `.ai-dlc/publish.toml`
- **THEN** the plan is refused naming the missing file

### Requirement: KC-04 Publication is reviewed and version-guarded

`publish-plan` SHALL return the action, site, space, parent, page id, expected
version, title and the exact body without frontmatter or operation markers, and
SHALL write nothing. For a note bound to a page it SHALL require the page's current
version and refuse when it differs from the recorded `publish.version`.
`publish-record` SHALL write `page_id` and `version` into `publish`, preserving the
rest of the note. It SHALL refuse a different page id or a version not newer than
the recorded one, and report an identical repeat as unchanged.

#### Scenario: The page changed since publication
- **WHEN** a bound note records version 3 and the page's current version is 4
- **THEN** the plan is refused with a version conflict

#### Scenario: Recording a new page
- **WHEN** a planned note is published as page 4242 version 1 and recorded
- **THEN** its frontmatter holds the page binding and the rest of the note is unchanged
