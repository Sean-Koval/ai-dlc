---
name: handoff
description: Use when preparing another person or agent to continue work.
---

# Handoff

Produce a handoff with objective, current branch/work reference, verified state, remaining risks, next action, and authoritative links. Reference the specification role for formal requirements, tracker for state, and repository for decisions. Preserve uncertainties. Ask services to store/link only when requested; omit credentials and personal notes irrelevant to the recipient.

Resolve provider-specific commands from the configured role provider’s instructions. The agent supplies judgment; services store, validate, and link artifacts.

When a selected session lesson should persist, use `learnings/<YYYY-MM-DD>-<work-id>.md`
with front matter `work`, `repository`, `pr`, `tags`, then `## What happened`,
`## What to do differently`, and `## Links`. Keep it short and link source evidence.
The format is documented in AI-DLC's `docs/design/local-and-shared-knowledge.md`.
Pass the authored file to `ai-dlc work finish <id> --learning FILE` (MCP
`work_finish` accepts `learning` text), or use the knowledge provider's `note`
operation with a stable operation ID. A pending learning does not undo verified
completion; retry the same body instead of duplicating it. Never copy raw logs.
