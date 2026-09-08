## 1. Implementation and verification
- [x] 1.1 Record approved bounded contract and recovery design.
- [x] 1.2 Test then implement provider identity, ledger, lifecycle and common onboarding.
- [x] 1.3 Cover Registry/WorkService transport, lost responses, concurrency and file safety.
- [x] 1.4 Pass required checks and strict OpenSpec; record exact evidence limits.
- [ ] 1.5 Obtain independent review before integration.

## Independent review repairs
- [x] 2.1 Reproduce and repair stale terminal-state validation and blocking FIFO intent reads, retaining no-retry recovery.
- [x] 2.2 Pass affected provider/WorkService/onboarding/component tests and format/lint/type checks; record exact evidence limits.
- [ ] 2.3 Obtain narrow independent acceptance before coordinator integration and final required checks.
