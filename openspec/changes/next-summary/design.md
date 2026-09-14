# Replace the JSON context brief with a readable what-next summary

## Context
`build_context` returns records as written and a fixed sentence. `read_work_records` (added with work artifact validation) already reads every record offline, validates shape and local artifacts, and deliberately does not resolve provider bindings. The session-start hook returns a one-line instruction. Nothing local records that a record was finished: `ai-dlc work finish` writes to the machine-local operation journal and the tracker, not to the record.

## Goals / Non-Goals
Give a person or agent a readable list of active records with the next command for each, in under a second, with no `gh`, `git` or network access. Keep the machine-readable `context` unchanged. Do not consult the tracker and do not change `work status`, which does.

## Decisions
- States are derived only from the `tracker`, `pr` and `spec` artifacts plus `requires_spec`. A `spec` under `openspec/changes/` but not under `openspec/changes/archive/` is unarchived; any other reference, or `requires_spec = false`, counts as archived because there is nothing local left to archive.
- Finish is not guessed. A record with a pull request and an archived change is printed as `awaiting merge` with `next: ai-dlc work finish <id>`, and the header says the tracker was not consulted. The `--all` flag adds `unpublished` records; there is no local finish evidence to filter on, so the default list is every record that has a tracker artifact.
- Lines are ordered by how actionable they are for a new session: `in progress`, then `awaiting merge, archive first`, then `awaiting merge`, then `unpublished`, and by ID within a state. The session-start hook keeps only the first ten lines, so the work an agent should continue comes first.
- The next command for `in progress` is `ai-dlc work pr <id>`, which issue #73 delivers; the summary names the command the workflow intends rather than a workaround.
- The text is rendered by the work package and printed verbatim by the CLI; the hook calls the same function and falls back to the previous one-line instruction when the project cannot be read, so a broken record never blocks a session start.
- `--json` returns an object with a `status` string and the record list rather than a bare list, following the repository's result-envelope rule; the fields per record are exactly `id`, `state`, `tracker`, `pr` and `next`.
- Rejected: reading the operation journal for finish evidence. It is machine-local, keyed by binding fingerprints, and absent in a fresh checkout, so it would make the summary differ between machines.

## Risks / Trade-offs
In a repository whose finished records were never pruned, most lines say `awaiting merge`. That is honest and cheap; the ordering keeps in-progress work visible in the hook's ten lines.

## Migration Plan
No record changes. `scripts/cloud/claude-session.sh` keeps calling `ai-dlc context --brief` and now prints the readable text.
