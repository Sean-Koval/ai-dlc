# Design: second brain phase A

## Context

ai-dlc already has a locked, idempotent vault writer and one frontmatter schema
with source hashes. Confluence is reached through whatever Atlassian connection the
client has approved; at work that is the company's Rovo MCP. ai-dlc must not add a
second connection or carry credentials.

## Decisions

### The guard is local code; the call is the agent's

`publish-plan` and `publish-record` decide everything checkable on the machine:
schema, the origin/site wall, the version guard and the write-back. The agent makes
the Confluence call between them, after the user confirms. A future adapter can
implement the `publish` contract operation without changing the skills.

### Each vault declares its own target

`<vault>/.ai-dlc/publish.toml` names `origin`, `site`, `space` and an optional
`parent`. It lives with the vault, so two vaults cannot share a default. A
missing file refuses publication. Sites are bare host names compared exactly.

### Published state is the binding, not a status

A note is published when `publish.page_id` and `publish.version` are set. `status`
stays reserved for decision records, so existing validation is unchanged.

### Origin is required on captures only

Requiring it everywhere would invalidate every existing learning and ADR. A
`publish` block also requires it, so no note can be published without one.

### Dedupe by normalized digest

The digest ignores CRLF versus LF, so a re-export of the same transcript matches.
Pasted threads are hashed from a temporary file outside the vault.

## Risks

- YAML comments in a note's frontmatter are lost when `publish-record` rewrites it.
- A changed Confluence page is detected only when the agent supplies its current
  version; the skill requires it before every update.
