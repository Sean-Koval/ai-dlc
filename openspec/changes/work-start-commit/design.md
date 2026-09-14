# Collapse the delivery path: start commits its record and pr opens the pull request

## Context
`WorkService.branch` refuses to switch branches while any file other than the work record is dirty, then `WorkService._start` and `WorkService.link` save the record. The saved record is left uncommitted, so every delivery began with a hand-written `chore(work)` commit. `GitHubSCM` wraps `gh` for merge and workflow evidence but has no pull-request creation operation, so agents ran `gh pr create` by hand and then `work link <id> pr <url>` by hand, leaving a second uncommitted record edit.

## Goals / Non-Goals
Make each gap between existing gates one command. Only the record file may ever be staged by these commands. A retry must never open a second pull request. Not in scope: auto-merge, review requests, CI polling, archiving the specification change, or pushing on the caller's behalf.

## Decisions
- One record commit helper. Start and link share a helper that stages only `.ai-dlc/work/<id>.toml` and commits with `git commit --only -- <record>`, so other staged or dirty files are neither included nor disturbed. When the record has no change against `HEAD` nothing is committed, so a repeated start stays idempotent. The commit messages are `chore(work): start <id>` and `chore(work): link <kind> for <id>`.
- `--commit` defaults on; `--no-commit` keeps the previous behaviour for callers that batch record edits. The MCP tools use the same service defaults.
- `pull_request_create` is an optional SCM contract operation, so existing executable SCM providers remain conformant. The GitHub adapter checks `git rev-parse --abbrev-ref <head>@{u}` and refuses with the remedy "push the branch first" instead of pushing implicitly; pushing is a deliberate act the harness hooks already govern. The body is passed through `--body-file` so Markdown reaches `gh` unchanged, and the returned URL must belong to the configured repository.
- `work pr` uses the head branch the record binds, not whatever branch is checked out, so the pull request cannot be opened from an unrelated checkout. It requires a started record.
- The body renderer is pure and lives beside `render_ticket_body`: title from the record, `## Scope`, `## Acceptance`, and `Closes #<n>` only when the tracker provider's kind is `github-issues` and the reference is a bare issue number, since only then does GitHub interpret the keyword.
- Creation is journaled under an SCM-scoped operation identity. A succeeded journal entry is reused, so a crash between creation and linking still links the recorded URL rather than creating again. An uncertain entry refuses with a remedy to find and link the pull request by hand: the contract has no pull-request search, and inventing one would widen the SCM contract for a rare recovery case.
- Rejected: pushing when the upstream is missing. Rejected: opening the pull request inside `work start`; starting is local and reversible, opening a pull request is a remote publication that needs pushed commits.

## Risks / Trade-offs
`--commit` writes a commit on the caller's branch. It only ever contains the record, is skipped when the record is unchanged and can be turned off. The GitHub adapter's stdout parsing depends on `gh pr create` printing the pull request URL, which it has done since 1.0; a mismatch fails closed.

## Migration Plan
No record changes. Projects that adopted the previous guidance can keep committing by hand with `--no-commit`. The regenerated contract schemas add one optional operation.
