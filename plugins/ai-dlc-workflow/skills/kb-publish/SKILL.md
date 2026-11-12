---
name: kb-publish
description: Use when the user asks to publish, promote, push or share a vault note (a meeting note, knowledge note, weekly rollup or decision write-up) to Confluence. One-way and reviewed - shows the exact outgoing page, needs confirmation, and records the page id back in the note.
---

# KB publish

Publishing needs `ai-dlc` on PATH. Without it, stop: never publish unguarded.

1. **Plan.** Run `ai-dlc knowledge publish-plan NOTE --vault VAULT`. A refusal is
   final: report its reason. Never edit `origin`, `publish.site` or
   `.ai-dlc/publish.toml` to get past one. Daily notes are always refused.
2. **Search before create.** For a `create`, search the planned space for the
   title. If a page already exists, stop and ask: retitle, or skip. Never overwrite
   a page the note is not bound to.
3. **Check the version.** For an `update`, read the bound page's current version
   and rerun the plan with `--remote-version N`. A version conflict means someone
   edited the page; it is now the record, so stop.
4. **Show and confirm.** Show the site, space, parent, title, action and the full
   body exactly as planned. Publish only after an explicit yes; any change to the
   note means planning again.
5. **Publish** the planned body through the Atlassian connection for the planned
   site. If the connected site is a different one, stop.
6. **Record.** Run `ai-dlc knowledge publish-record NOTE --vault VAULT --page-id ID
   --version N` with the result, then give the page link.

After publishing, the page is the record: edits happen in Confluence, never back
in the vault. Filing proposed tickets is separate and needs its own confirmation.
