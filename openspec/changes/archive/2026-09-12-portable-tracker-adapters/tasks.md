## 1. Implementation and verification

- [x] 1.1 Consume capability discovery delivered and independently reviewed in github-ticket-workflows / PR #23; preserve legacy adapter behavior.
- [x] 1.1a Consume the delivered GitHub repository/account setup, lifecycle/recovery tests and disposable live qualification from PR #23. Common connection extraction remains under #19.
- [x] 1.2 Implement and independently review the bounded Plane lifecycle/connection child, including TDD repairs and mapped local checks.
- [x] 1.3 Implement and independently review the bounded Jira Cloud new-work child, including TDD required-field repairs and mapped local checks.

## 2. Review and finish


[Execution plan](2026-09-06-portable-tracker-adapters.md). GitHub/capability scope is delivered. Bounded Jira and Plane implementations are reviewed; their child specifications are archived under2026-09-08. Deployment qualification and parent finish remain open.
Implement Jira Cloud for new work before the optional Plane slice; no Jira migration.

## Deferred live qualification — not delivered

These steps were never performed and are **not** satisfied by this archive. Issues
#14/#15/#16/#17/#20/#21/#22 were cancelled (NOT_PLANNED), not completed, and the
outstanding evidence remains tracked in
[release verification](../../../../docs/release-verification.md). Archiving records the
delivered scope's requirements as obligations; it asserts no live qualification.

- [ ] 1.2a Qualify the Plane lifecycle against the selected real deployment/account; fixture evidence does not complete this step.
- [ ] 1.3a Qualify Jira against the actual selected work deployment/account and workflow.
- [ ] 2.2 Independent review recording actual live evidence for the deferred deployment qualification.
