# Rehearse a reviewed behavior check

Use the team's existing test tools. This shows one reviewed check detects one
concrete regression; it does not score the suite or pick a universal framework.

1. **Inspect sources.** Read `[setup.steps]`, `[checks.commands]`,
   `checks.required`, `.mise.toml` (including an empty `[tools]` table), test-runner
   configuration, manifests, CI commands and the relevant requirement or acceptance
   source. Record exact paths, the behavior each source establishes and unknowns.
   Do not infer coverage from filenames, a syntax check or successful setup.
2. **Propose and review the mapping.** In the delivery slice, record requirement
   and check IDs, observable behavior, inspected sources and the exact team-owned
   command. Add prerequisites, the required/optional choice, unknowns and the
   review source. Use existing authorization; do not add a second approval ritual.
   Change shared configuration only after this review, preserving authored
   tests, required IDs and unrelated commands.
3. **Prepare the normal runner.** Run the reviewed setup action separately through
   `ai-dlc project setup`; a check never installs its own tools or silently changes
   shell. `mise` is required for `ai-dlc project check` even when the tools table is
   empty. If runtime resolution reports it unavailable, no check ran and no passing
   receipt exists. Direct shell execution is diagnostic only.
4. **Preflight an external disposable fixture.** Copy the reviewed fixture to an
   explicit temporary location outside the active checkout. Record the source
   revision and fixture identity, and keep the exact original bytes. Stop if the
   fixture is in the active checkout, isolation is uncertain, or the exercise
   would use production data or mutate a remote service.
5. **Observe pass, regression failure, restored pass.** In the disposable copy,
   run `ai-dlc project check --check CHECK_ID` and require a pass. Introduce only
   the reviewed regression, rerun it and require the expected failure. Restore
   the saved bytes, verify the fixture matches its baseline, and require a final
   pass. If the changed behavior still passes, or any outcome is unobserved, the
   rehearsal is incomplete.
6. **Retain bounded evidence.** Record requirement/check IDs, exact command,
   engine and runtime identity, fixture/source identity, the deliberate change,
   all three outcomes and limitations. This demonstrates detection only for the
   selected behavior. It does not establish complete adequacy, human quality,
   productivity, native-platform qualification or comparison results.

Never alter the active checkout to manufacture a failure, and do not change the
test until it appears successful.

A focused receipt is edit feedback. It retains the full configured required list
and cannot satisfy missing completion outcomes. After target-branch integration,
run `ai-dlc project check --required` for complete required evidence.
