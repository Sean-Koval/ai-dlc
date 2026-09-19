## Why

AI-DLC's checks prove that its own commands behave. Nothing yet shows whether a
coding agent given AI-DLC delivers better work than the same agent without it, or
whether the agent follows the workflow at all. Issues #137–#141 describe a full
end-to-end evaluation capability and cite this change for its design, which was
never committed. This change specifies only the first increment (#137) and adds
the one thing the issue text omits: a baseline arm, so the first result answers
"does AI-DLC help?" before more evaluation machinery is built.

The maintainer reviewed this scope on September 18, 2026 and kept the baseline arm
(EE-05), which is an addition to the scope recorded in #137.

## What Changes

- Add `ai-dlc eval plan|run|report` as thin CLI entry points over a new
  `verification/evaluation` service.
- Add versioned scenario, execution-profile, normalized-event and run-report
  contracts under `contracts/`.
- Add a disposable Docker attempt lifecycle that installs a candidate wheel
  through bootstrap, reusing the fail-closed controls in `verification/sandbox.py`.
- Add an arm to every scenario: `treatment` (AI-DLC installed and rendered) and
  `baseline` (the same image, fixture and goal with AI-DLC absent).
- Start with a deterministic command driver. Real client adapters are #138.

## Capabilities

### New Capabilities
- `end-to-end-evaluation`: planned, isolated, independently observed evaluation
  attempts with separate workflow, correctness and quality results per arm.

## Impact

New verification subpackage, contracts, one fixture project with hidden
acceptance tests, tests, and a runbook section. Existing provider conformance
(`provider test`) and prompt-only skill evaluation interfaces are unchanged. No
cloud credentials, live providers or CI lanes are introduced; #138–#140 stay open
and are decided after the first treatment-versus-baseline report.
