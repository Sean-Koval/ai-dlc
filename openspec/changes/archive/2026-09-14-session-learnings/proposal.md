# Capture session learnings at finish and recall them at work start

## Why
Knowledge is linked, not fed. An Obsidian vault can be linked and mounted and `knowledge find`, `knowledge note` and `knowledge append` exist, but nothing records what a session learned and nothing reads it back before the next session starts. `work finish` already journals an optional handoff through the knowledge role; a learning note has no such path, so the `day-end` skill's "capture selected learning" instruction has no command behind it. Issue #82 records the gap and the one idea worth borrowing: a local friction signal, a short learning note, and a bounded recall before work.

## What Changes
- `work finish <id> --learning FILE` (MCP `work_finish(learning=...)`) SHALL store the note at `learnings/<YYYY-MM-DD>-<work-id>.md` through the knowledge provider's idempotent `note` operation under a journaled operation identity, so a retried finish stores it once. Finishing without a learning SHALL still complete and report a one-line reminder.
- `work start <id>` and the `session-start` hook SHALL recall up to five stored learning notes whose path or body matches the record's title words or its specification change name, returning each path with its first content line. An absent vault or no match SHALL produce nothing and SHALL NOT fail the command.
- The hook SHALL count friction per session from the payloads it already receives, hook denials, blocked or failed `work` results and repeated identical commands, in `.ai-dlc/local/session/`. The `stop` event SHALL add a learning-note reminder only once the count reaches the threshold of three. Nothing is transmitted.
- The learning note format is defined in the local and shared knowledge design; the `day-end` and `handoff` skills point at it and `day-start` reads recalled notes.

## Capabilities
### New Capabilities
- session-learnings: Optional idempotent learning storage through the knowledge provider, bounded read-only recall, and a local friction counter.

## Impact
`WorkService.finish` and `WorkService.start`, the `work finish` CLI and MCP surfaces, the knowledge module's read-only recall, the harness hook, three skills and their rendered copies, the knowledge design document and both tool maps. No tracker, SCM or finish gate behavior changes; the knowledge provider remains the only vault writer and no network call is added.
