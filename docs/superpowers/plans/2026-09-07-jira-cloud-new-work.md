# Jira Cloud new-work implementation plan

Authorized bounded child of issue20, after common connection service. Current
parent priorities are Jira Cloud new work first, Plane optional, no Jira migration.

1. Verify current official REST/auth/schema facts and write JC01–06 before code.
2. Record failing HTTP-transport tests for identity/auth, exact ADF/property
   correlation, complete pagination, metadata/state refusals and remote links.
3. Implement provider-only REST behavior and central registration; no WorkService,
   CLI or provisioning vendor branches. Add common declarative discovery/selection.
4. Exercise the real Registry, WorkService, journal and local files with HTTP
   fixtures, including delayed create visibility, PR linking and gated completion.
5. Document exact local setup examples, supported fields/auth, request/search
   budgets, cross-machine uncertainty and separate tenant qualification.
6. Freeze source, run all required checks and strict validation, record evidence,
   commit clean candidate and obtain independent review before integration.

No helper agents, company API calls, migration, deployment, archive, PR, merge or
finish. Root coordinates delivery. The local runtime uses a worktree-specific
prepared environment after the shared bootstrap executable stalled; evidence must
not claim that concurrent shared-bootstrap publication passed qualification.
