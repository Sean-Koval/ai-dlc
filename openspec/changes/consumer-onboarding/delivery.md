# Consumer onboarding distinct from engine contribution

Priority: P0. Type: independently deliverable feature specification. Status: proposed; implementation owner unassigned. Product decision owner: Sean Koval.

## Problem and outcome

A teammate who clones AI-DLC for another project is sent into source-contributor checks and POSIX setup without a clear target-project or platform boundary. Provide a truthful consumer route and read-only plan so the teammate knows what to install, enroll, adopt and verify in their own repository. Source installation alone must not enroll that project into the engine's personal tracker or vault.

## Approved scope versus proposed design

The user authorized specifications and detailed issues from the PM review. The product promise is authoritative; the proposed `project onboard` schema and implementation below require review before coding. Publication of this issue does not mean those recommendations shipped, passed qualification or were approved for execution.

## Scope and acceptance

- CO-01: Installation, explicit enrollment, target adoption and contribution have separate routes. A downstream example ends in a target behavior check, not engine full tests.
- CO-02: `project onboard --root PATH` is read-only, no apply flag, explicit selections, no source fetch/process execution/writes. Missing/conflicting inputs block with exact remediation.
- CO-03: Ordered existing command recommendations carry argument arrays, dependencies, effects and review requirements. Actionable planning is never reported as completed setup or native readiness.
- CO-04: Supported Unix delivery includes honest pre-import Windows limits. No mandatory WSL, container fallback, shell translation or invented client support.
- CO-05: Repeat calls reflect observed state. Test preservation and no effects; record a real supported-platform downstream journey and keep unavailable qualification pending.

## Delivery approach and dependencies

Reuse setup/readiness, enrollment, adoption and native-render ownership services behind a shared application service; CLI remains thin. Deliver without depending on native Windows setup/runtime work. Future Windows support updates the support result after its own evidence. Installed-client and Windows walkthrough evidence remains #53.

## Errors, evidence and costs

Missing target/selection, configuration conflict, unsupported platform/shell/client and missing release feature must be explicit. Invalid arguments/configuration exit 2; blocked plans exit 1; actionable plan exit 0. Record test commands and real fixture identity, elapsed time/manual steps and observed limitations without fabricated savings. No paid evaluations, automatic login, package installation or provider writes are required by preflight.

## Ownership, exclusions and documentation

Do not copy private profiles into shared state, infer accounts, or expose secrets/private shell content. Exclude new installers, a persistent wizard/orchestrator and broad Windows qualification. Update existing README, machine-enrollment runbook, work-computer setup, tool map, release limits and affected portable guidance during implementation; record actual documentation dispositions.

## Authoritative artifacts and review

Product brief: [product direction](../../../docs/product-direction.md). Formal scope: [proposal](proposal.md), [design](design.md), [CO requirements](specs/consumer-onboarding/spec.md). The [tasks](tasks.md) are the authoritative unchecked implementation checklist; this issue does not duplicate each checkbox. Review status remains proposed until a recorded product/engineering disposition. Do not claim delivery based only on this planning issue.
