# Validate work record artifact references as a repository invariant

## Why
Archiving an OpenSpec change moves its directory, and every `spec` artifact in this repository's work records is a bare `openspec/changes/...` directory. `artifact_is_local` classified such a reference as local only while the path existed, so the moment archiving moved it the reference was reinterpreted as an opaque provider-native identifier and skipped. Nothing else reads `.ai-dlc/work/` either: the seven required checks never open a work record, and `ai-dlc work validate` is per record.

On 2026-09-12 the archives in #64 and #65 broke three records' `spec` references and one `plan` reference; all were found by hand and repaired in #66 and #67. Issue #68 records the measurement: 40 of 40 `spec` artifacts were bare directories, and validating a record whose `spec` pointed at `openspec/changes/gone-missing` returned valid while every required check passed.

## What Changes
- A suffix-less `spec` reference whose leading path segment is an entry of the repository root SHALL be classified as a local artifact whether or not the referenced path currently exists, so a moved directory is reported as absent.
- Genuine provider-native identifiers, including opaque slash IDs and provider URIs, SHALL remain provider-owned and unprobed.
- `ai-dlc work validate --all` SHALL validate every record under `.ai-dlc/work/` together: record shape, local artifact references and the dependency graph, offline, without resolving provider bindings and without a journal.
- This repository and the project template SHALL run that validation as the required `work-records` check.

## Capabilities
### Modified Capabilities
- spec-delivery-traceability: Repository-anchored specification paths stay validated after they move, and every record's artifacts are validated together as a required check.

## Impact
The pure locality classifier, work validation, the `work validate` command, this repository's check manifest, the project template's check manifest, delivery guidance and their tests. No binding, journal, publication, start or finish behavior changes. Finished records keep their historical fingerprints; the repository-wide check deliberately does not read bindings because drift is a mutation-time refusal, not a repository invariant.
