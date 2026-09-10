## 1. Implementation and verification

- [x] 1.1 Consume capability discovery delivered and independently reviewed in github-ticket-workflows / PR #23; preserve legacy adapter behavior.
- [x] 1.1a Consume the delivered GitHub repository/account setup, lifecycle/recovery tests and disposable live qualification from PR #23. Common connection extraction remains under #19.
- [x] 1.2 Implement and independently review the bounded Plane lifecycle/connection child, including TDD repairs and mapped local checks.
- [ ] 1.2a Qualify the Plane lifecycle against the selected real deployment/account; fixture evidence does not complete this step.
- [x] 1.3 Implement and independently review the bounded Jira Cloud new-work child, including TDD required-field repairs and mapped local checks.
- [ ] 1.3a Qualify Jira against the actual selected work deployment/account and workflow.

## 2. Review and finish

- [ ] 2.1 Run required project checks and strict validation of this change.
- [ ] 2.2 Complete independent review and record actual live evidence or explicit unverified gates.
- [ ] 2.3 Archive only delivered scope, link PR/CI evidence, and finish the reviewed implementation work through the configured workflow.

[Execution plan](2026-09-06-portable-tracker-adapters.md). GitHub/capability scope is delivered. Bounded Jira and Plane implementations are reviewed; their child specifications are archived under2026-09-08. Deployment qualification and parent finish remain open.
Implement Jira Cloud for new work before the optional Plane slice; no Jira migration.
