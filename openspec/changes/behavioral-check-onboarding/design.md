# Behavioral check onboarding design

## Context and observed behavior

Authority is [product direction](../../../docs/product-direction.md), particularly useful local checks, small artifacts and measured outcomes. `portable-development` already owns PC-01 focused checks, PC-02 full completion evidence and PC-03 behavioral Python starters. `connected-project-readiness` RD-04 already requires actionable runtime failures. These contracts are retained, not replaced.

`setup/project.py` resolves mise before checks, including an empty tools table. The evaluation runbook records a candidate that adopts and renders successfully but cannot execute the normal runner because mise is absent. Existing adoption preserves authored checks and tests; new Python greeting tests are a starter example rather than a team's acceptance suite. The intended addition is guided selection and observable rehearsal, not an inference that current checks are inadequate.

## Decisions

1. Use existing guidance and setup/check interfaces. First inspect declared checks, setup steps, test configuration, CI commands and relevant requirement evidence. Present only source-grounded commands and uncertainties. The maintainer or authorized harness reviews the proposed requirement/check mapping before shared configuration changes. No framework is selected from filenames alone.
2. Keep command ownership explicit. Reuse the team's commands and selected shell/runtime contract. Any prerequisite installation is a separate reviewed setup action. A check never installs dependencies or repairs itself. Generated guidance links this workflow without expanding always-loaded context into a testing tutorial.
3. Preserve mise as the existing execution contract. Onboarding must name its requirement, even when `.mise.toml` contains no tools, and use existing runtime diagnostics/remedies. A missing runtime cannot produce passing evidence. For the deferred comparison, prepare a suitable common base runtime for both arms and smoke the ordinary candidate runner without a model call; do not introduce treatment-only runtime advantages.
4. Demonstrate sensitivity safely. Use an explicit disposable fixture/copy with a recorded baseline and no connection to the team's deployment or production data. Run the reviewed behavioral check successfully, introduce one reviewed behavior regression in that fixture, observe its failure, restore the fixture and observe success. Do not sabotage the active checkout, reuse its dirty files as a reset target, or mutate remote state. A failed isolation preflight stops the rehearsal.
5. Retain a concise result: requirement/check IDs, command, engine/runtime identity, fixture/source identity, expected change, three outcomes and limitations. Store disposable logs under ignored local state; durable qualification belongs in existing verification ownership only when reviewed. No result claims complete test adequacy, team productivity or product quality.

## Compatibility and trade-offs

The main cost is one deliberately bounded rehearsal. It provides stronger evidence than another configuration checklist without installing another test platform. Existing projects retain their tests, required IDs, optional commands and receipt contract. Focused checks remain iteration feedback and cannot satisfy missing full completion outcomes. Python starters continue working as before. No native-Windows claim follows from POSIX fixtures; the Windows slice owns its platform runner and qualification.

## Documentation and verification

Update current development/adoption guidance and the evaluation prerequisite section, with catalog mappings and content-bound dispositions only for impacted targets. Test existing-project preservation, reviewed command selection, missing runtime, isolated negative rehearsal and focused/full receipt behavior. Execute one real local rehearsal using the normal runner; image smoke is separate evidence from paid comparison and native client qualification.

## Inputs and boundaries

The team's concrete requirement and test command must be selected during actual adoption by its maintainer. This is an explicit per-project input, not a missing product decision or license to choose a universal framework. The paid comparison remains deferred. No dependency on other proposed team-adoption changes is required; integration with their platforms is qualified separately.
