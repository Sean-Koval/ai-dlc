## 1. Implementation and verification

- [x] 1.1 Consume capability discovery delivered and independently reviewed in github-ticket-workflows / PR #23; preserve legacy adapter behavior.
- [x] 1.1a Consume the delivered GitHub repository/account setup, lifecycle/recovery tests and disposable live qualification from PR #23. Common connection extraction remains under #19.
- [ ] 1.2 Implement and qualify the Plane lifecycle adapter and connection handler; demonstrate failing regressions before implementation and run the mapped focused checks.
- [ ] 1.3 Implement and qualify Jira against the selected work deployment; demonstrate failing regressions before implementation and run the mapped focused checks.

## 2. Review and finish

- [ ] 2.1 Run required project checks and strict validation of this change.
- [ ] 2.2 Complete independent review and record actual live evidence or explicit unverified gates.
- [ ] 2.3 Archive only delivered scope, link PR/CI evidence, and finish the reviewed implementation work through the configured workflow.

[Execution plan](../../../docs/superpowers/plans/2026-09-06-portable-tracker-adapters.md). Only the explicitly checked delegated GitHub/capability scope is delivered.
Implement Jira Cloud for new work before the optional Plane slice; no Jira migration.
