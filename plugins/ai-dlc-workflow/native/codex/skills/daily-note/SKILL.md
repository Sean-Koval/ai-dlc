---
name: daily-note
description: Use when the user starts or ends a work day, says "today", "daily", "daily note", "standup", "what's open" or "end of day", or asks for a weekly rollup per project or lane. Opens or creates Daily/YYYY-MM-DD.md in the configured Obsidian vault with a read-only summary of each lane's Jira epic.
---

# Daily note

The vault is the configured `paths.vault`. Its `origin` (`work` or `home`) is in
`<vault>/.ai-dlc/publish.toml`; if it is missing, ask which vault this is. Never
default it, and never read or write the other vault.

## Start of day

1. Open `Daily/YYYY-MM-DD.md`, or create it with this frontmatter:
   `id: daily/YYYY-MM-DD`, `kind: daily`, `scope: personal`, `label: internal`,
   `author`, `valid_from`, `origin`, and `lanes:` listing epic keys. Reuse
   yesterday's `lanes:` when the user names none.
2. For each lane, read its epic's children from the tracker connected for this
   origin: open, blocked, and decisions waiting on someone. Use the epic's saved
   filter if one exists. Write a `## Lanes` section with one linked line per item.
3. Read only. Never create, comment on, label or transition a ticket from here.

## End of day

Append `## Moved` under a stable operation ID (`daily-YYYY-MM-DD-end`): tickets
that changed status, merged pull requests and notes captured today, each linked.
Add `## Carry over` for anything still open from `## Lanes`.

## Weekly rollup (on request only)

For each lane, gather the week's `## Lanes`, `## Moved` and meeting notes with that
`lane`. Write `Weekly/YYYY-Www-<lane>.md` as `kind: note` with the same `origin` and
`lane`. Neither a rollup nor a daily note is written to the wiki; only
`ai-dlc knowledge render` writes it, from merged records.

When `ai-dlc` is on PATH, write with `ai-dlc knowledge note` or `append`
(`--operation-id`, `--vault`) so a retry does not duplicate text. Work-origin
content stays on the work machine and in the company's own systems.
