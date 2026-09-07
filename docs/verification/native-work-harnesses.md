# Native work harness qualification

This is a project-only child of #19. No global Antigravity configuration, new hook
support, work-system credentials or live client qualification is implied.

The initial TDD cycle reproduced a missing Claude HTTP type, six unsupported
Antigravity behaviors and an ambiguous transport acceptance. Nine native tests
then passed; 71 affected renderer/readiness/hooks/personal-client tests, lint,
format, types and root generated-file checks passed.

The combined native/product-shaping candidate `7eeca51` passed all five required
checks on a clean tree, including 1,154 tests in 241.77 seconds. The ignored local
receipt is `native-shaping-required.json`. This is pre-review-fix candidate evidence.

Independent review requested two P2 fixes: custom provider links inside the
nested native rule were not rebased, and readiness could remain ready after a
selected skill or MCP file disappeared. A P3 runbook comment requested the actual
GitHub connection command. Four new red cases reproduced those two defects and a
related native metadata preservation problem. The repair rebases every validated
provider link, verifies complete native rendering during offline readiness, and
uses a managed rule section so client/user metadata outside it survives updates.
The runbook links the actual saved-plan connection workflow. The corrected scope
passes 79 affected tests plus lint/format/types and strict native OpenSpec checks.
Independent re-review found no P1/P2 defects and requested a P3 legacy-upgrade
regression. Two real filesystem cases now seed the exact prior whole-file rule:
intact owned content upgrades cleanly, while authored edits refuse without writes.
All 15 native tests pass. Final combined required checks remain pending.

Official client schemas were inspected on September 7 and linked in the design
and runbook. Emitted configuration and real filesystem tests establish offline
behavior only. Record actual OS/architecture, client edition/version, rule
activation, skill recognition and harmless MCP listing/authentication on the work
laptop before native qualification. Environment interpolation for Antigravity is
explicitly unsupported until its selected version contract is qualified.

## Delivery checklist

- [ ] Independent re-review accepts the corrected implementation.
- [ ] Final combined required checks and strict specifications pass.
- [ ] Archive the completed behavior and review archive references.
- [ ] Integrate through a reviewed PR and exact merged-revision evidence.

Parent #19 remains open for its undelivered common onboarding/toolset scope.
