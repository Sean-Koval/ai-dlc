---
name: handoff
description: Use when preparing another person or agent to continue work.
---

# Handoff

Produce a handoff with objective, current branch/work reference, verified state, remaining risks, next action, and authoritative links. Reference the specification role for formal requirements, tracker for state, and repository for decisions. Preserve uncertainties. Ask services to store/link only when requested; omit credentials and personal notes irrelevant to the recipient.

Resolve provider-specific commands from the configured role provider’s instructions. The agent supplies judgment; services store, validate, and link artifacts.

For delivery, use `ai-dlc work start <id>` and, after checks and an explicit branch push, `ai-dlc work pr <id>`. Start and link commit only the work record by default (`--no-commit` opts out). Push the PR-link commit before review. Include the linked PR URL; repeated PR creation returns that link. Report an uncertain creation and recover by inspecting the SCM and linking its existing PR.
