# Workflow-bundle successful-backup retention repair

Work: [GitHub issue 10](https://github.com/Sean-Koval/ai-dlc/issues/10),
`portable-workflow-bundles`. Repair baseline: `04c65cb`, which includes the
accepted failed-stage retention fix `83d0718`. The existing isolated branch is
`codex/portable-workflow-bundles`. This follow-on addresses the remaining
successful-render backup cleanup finding identified in the
[September 6 review](../planning/stage-cleanup-review-2026-09-06.md).
The older report's Linear status is historical; GitHub issue 10 is the current
successor. This repair does not reconcile the older work record's tracker binding.

## Behavior and scope

After successfully publishing and validating a bundle render, the renderer no
longer unlinks backups. An earlier identity check cannot make a later pathname
deletion safe against a same-user writer. This repair uses non-deleting retention;
it does not claim atomic cleanup or move the same check/unlink gap elsewhere.
Existing failure recovery, failed-stage retention, and diagnostic forwarding are
preserved.

The successful render result includes `retained_backups` when this invocation
retained backups: a sorted list of project-relative paths. The existing CLI JSON
output exposes the field. Backups can include previous managed guidance,
ownership records, and obsolete outputs removed from active guidance. They are
not entered into managed ownership or reused as trusted inputs. Preview and
unchanged apply retain their existing result shape. Later renders neither alter
the retained files nor repeat reports from prior invocations.

Record the render result. With concurrent writers stopped, inspect the exact
reported files, their types and contents. Preserve authored or uncertain content
before deliberate manual removal. Never remove all `.ai-dlc-*` files by pattern.
If an ancestor has moved, locate the reported filename in the displaced directory.
Backup accumulation and manual inspection are the explicit trade-off; no cleanup
command or collector is introduced.

The diff is limited to rendering, its regression tests, and this change's
specification/verification documentation. It does not modify bundle import tree
cleanup, provider adapters, source selection, tracker state, or completion gates.

## TDD evidence

Five new cases were run against the unchanged production code and failed:

- Three real-file cases replaced a validated backup with an authored regular
  file, edited its bytes in place, or replaced it with a symlink. Every case
  failed because successful cleanup deleted the pathname. After the repair,
  each checks the retained inode, authored bytes, active output, and reported path.
- Update and obsolete-output removal cases failed because backups were not
  retained/reported. They now also check read-only preview, complete residue
  reporting, exclusion from ownership, and a later unchanged apply preserving
  an authored edit to a retained backup.

All 51 rendering tests passed after the repair. Two existing recovery diagnostic
cases previously injected an error at the second backup unlink. That operation
no longer exists. Their fixture now seeds snapshot recovery without a named
backup directly, while real stage writes fail once or twice. Assertions continue
to cover the original exception object, restored output on retry, retained
partial-stage bytes, and forwarding every retained filename. These are recovery
state-machine tests, not a claim that successful rendering still deletes backups.

## Validation and remaining delivery

Source bootstrap completed with `sh scripts/bootstrap.sh --source`. Strict
OpenSpec validation passed with
`openspec validate portable-workflow-bundles --strict --no-interactive`.
The focused rendering command was
`.venv/bin/python -m pytest -q tests/test_rendering.py`.

`ai-dlc project check --required` passed all five required outcomes: generated,
format, lint, types, and test. The full suite passed 1,146 tests in 198.80 seconds.
The command used this checkout's prepared source environment first in `PATH`:
`/Users/seankoval/.local/share/ai-dlc/bootstrap/source-2836003460/bin`, followed by
the bootstrap tools directory. The receipt records the dirty pre-commit repair
at baseline `04c65cb`; it is not merged-revision CI evidence. `git diff --check`
also passed.

Independent review, integration with the current GitHub-tracker branch,
specification archive, PR/CI/merge evidence, and `ai-dlc work finish` remain
separate delivery steps. These local filesystem tests do not establish live
service verification or cross-platform release qualification.
