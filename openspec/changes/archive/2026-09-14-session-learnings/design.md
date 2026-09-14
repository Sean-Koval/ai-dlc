# Capture session learnings at finish and recall them at work start

## Context
`WorkService.finish` journals a handoff through `self.role(work, "knowledge", fallback)` under `op_id(work, "handoff")` and survives any provider failure with `completed,handoff_pending`. `Knowledge.note` refuses to replace an existing note that does not carry the operation marker and is idempotent for the same operation and body. `handle_hook` receives `pre-tool`, `session-start` and `stop` payloads and already keeps a one-shot reminder marker under `.ai-dlc/local/reminders/`. Personal knowledge is not a repository mirror: the agent writes the note, the tool stores it.

## Goals / Non-Goals
Store a learning once per work item, recall a bounded set before work, and surface a local friction signal. Do not rank, index, build a graph, share across a team, or send anything anywhere. Do not make the learning a finish gate.

## Decisions
- One journaled note path. Handoff and learning share a helper that begins a journal record, writes through the knowledge role, and marks the operation uncertain on failure, so a retry never duplicates and completion never fails because of the vault. The learning uses `note` (a fresh file with the marker) rather than `append`; `op_id` derives a distinct learning identity from the work and knowledge binding. A separate journal entry fixes the first UTC date/path before writing, so retries across days retain the destination.
- Path and format. `learnings/<YYYY-MM-DD>-<work-id>.md` with front matter `work`, `repository`, `pr`, `tags` and the sections `## What happened`, `## What to do differently`, `## Links`. The service stores the body the agent supplies; it does not generate the sections.
- Recall reads only. `Knowledge.recall(terms, limit)` filters `find` results to `learnings/` and adds the first content line after front matter and markers. Terms are the record's title words plus the final segment of its `spec` artifact (the change name); the first segment such as `openspec` would match every note. A missing vault, unconfigured `paths.vault`, a provider without `recall` or any read failure yields an empty list. `work start` adds `learnings` to its result; the `session-start` hook appends one line per match to its context. Both stay additive so concurrent changes to `work start` and the hook merge cleanly.
- Friction is a small local file. `.ai-dlc/local/session/<sha256(session_id)>.json` holds counters keyed by kind. The hook counts its own denials, a `pre-tool` command identical to the previous one in the session, and, when a payload carries a `tool_response`, a `work` command result whose status is `blocked` or a failure. Hashing the session id keeps arbitrary client identifiers out of file names, as the reminder marker already does. The `stop` reminder for friction is added under its own `friction` key beside the existing one-shot reminder and appears when the count is at least three.
- Rejected: a required PostToolUse hook, which would change the rendered client settings for every project; the counter reads a `tool_response` when present without requiring it. Rejected: reading recalled note bodies in full; only the first content line is returned.

## Risks / Trade-offs
Recall on title words is deliberately naive and may return unrelated notes; it is capped at five and read-only. The friction counter is a heuristic and under-counts failures when the client sends no tool responses; a denied repeated command can contribute both signals. Notes written by hand outside `learnings/` are not recalled.

## Migration Plan
No record or configuration changes. Projects without a vault see no new behavior beyond the finish reminder.
