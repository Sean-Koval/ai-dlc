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
