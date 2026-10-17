# Fall back to REST when the GitHub GraphQL endpoint is refused

## Why

`ai-dlc work finish` reads and closes the tracker issue through `gh issue view` and
`gh issue close`, and verifies the viewer and the configured Project through GraphQL.
Where a proxy or policy refuses the GraphQL endpoint, finish cannot complete although
every gate passed. [#226](https://github.com/Sean-Koval/ai-dlc/issues/226).

## What Changes

- The github-issues adapter recognizes an HTTP-level refusal of the GraphQL endpoint
  (403, 404 or 410, not a scope or rate-limit error) and then reads, closes, reopens and
  links the issue and verifies the viewer through REST.
- Projects v2 for a node-identified project has no repository-scoped REST route, so the
  Project is reported `reconciled = false` with the reason. Completion closes the native
  issue only; `reconcile_closed` is withheld, so rerunning finish where GraphQL is
  reachable reconciles the Project.
- Planning operations (`in_progress`, `prepare`) and other GraphQL failures still fail.

## Capabilities

### Modified Capabilities

- `github-ticket-workflows`: GT-02 allows issue-only completion when GraphQL is refused.

## Impact

Finish completes in GraphQL-restricted environments. No configuration change.
