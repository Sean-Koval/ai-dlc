---
name: capture
description: Use when given a meeting transcript or notes export (Zoom .vtt, .txt, a Google Meet or Gemini notes Doc export, anything in Inbox/meetings/), or pasted chat or Symphony thread text, to turn into a structured vault note with decisions, actions, knowledge and open questions. Proposes Jira tickets; never files them.
---

# Capture

The vault, its `origin` and the hard wall are as in daily-note: work-origin text
is handled only by tools approved on the work machine and never leaves them.

1. **Refuse duplicates.** Save pasted text to a temporary file outside the vault.
   Run `ai-dlc knowledge captured FILE --vault VAULT`; exit 1 means it was already
   captured, so stop and link the existing note. Without `ai-dlc`, search the vault
   for the file's `sha256sum`.
2. **Write the note.** A transcript becomes `Meetings/YYYY-MM-DD-<slug>.md`
   (`kind: meeting`); a thread becomes `Threads/YYYY-MM-DD-<slug>.md`
   (`kind: thread`). Frontmatter: `id`, `kind`, `scope: personal`,
   `label: internal`, `author`, `valid_from`, `origin`, `lane` (an epic key) and
   `source: {file: <vault path> | room: symphony:<room>, sha256}`. Record no message
   IDs and no participant list beyond named owners.
3. **Sections**, dropping empty ones: a two-line summary, `## Decisions`,
   `## Actions` (`- [ ] what — owner, due, lane`), `## Knowledge` and
   `## Open questions`. An action without a clear owner goes to Open questions.
4. **Keep only the link.** Never paste the raw transcript into the note. Ask
   whether to delete the export or move it per the user's retention policy.
5. **Propose, do not file.** End with a table of proposed tickets: summary, type
   (task or decision), lane epic and execution label. Nothing is created until the
   user picks rows and a later step files them.

When a captured ruling answers an open decision ticket, draft its Chosen and
Rationale from the user's own words and show the draft. Change no field and move
no ticket until the user confirms.
