# Repository organization verification

Base: `baa8629343e47f245e9a7f0b225935ac49aea446` (unmerged PR35).
Change: [repository organization](../../openspec/changes/repository-organization/).
This record describes local cleanup; it does not establish merged or live-platform qualification.

## Scope and provenance

- Forty-nine root Python modules became ten root modules plus responsibility-based
  packages. Public console entry points and provider contracts are unchanged.
- Root Rust-era plans moved into docs/archive/legacy. Twenty-six tool-specific
  planning artifacts moved into matching OpenSpec changes or the historical archive.
- Historical research and assessments are explicitly labelled. Current navigation
  and work records point to the relocated originals; dated JSON/hash snapshots
  retain their original observations. No new factual review dates were invented.
- CLAUDE.md imports AGENTS.md. The renderer preserves an exact plain reference
  and retains existing mixed-file ownership protections.
- The obsolete unlocked environment installer was removed. Rust snapshot sync
  remains in scripts/legacy; Python legacy scaffold assets remain packaged.
- The tracked Superpowers scratch report was removed; its code/verification
  history remains in Git and the existing GitHub-workflow verification record.
  Ignored local evidence was retained under .ai-dlc/local/previous-execution-evidence.
- A repository-specific required layout check rejects root plans, new flat Python
  modules, scratch directories and duplicate Claude context. It does not impose
  this source layout on adopted projects.

## Verification

The plain-reference regression failed in both fresh and pre-existing-file cases
before implementation; all 61 rendering tests passed afterward. The layout
regressions failed before the new check existed and all four passed afterward.
The focused rendering, sandbox and packaging suite passed 391 tests.

The initial full run exposed residual compound test imports and a second provider
readiness parser that still required Claude markers. The imports were corrected;
provider readiness now uses the same validated guidance helper. The pre-fix
readiness case failed as expected. Independent review inspected source moves,
subprocess paths, packaging and authored-file protections; its one stale source
reference was repaired. Follow-up review approved the shared readiness validator.

Run `ai-dlc project check --required` for the full local result. It covers layout,
generated files, formatting, lint, types, tests and documentation dispositions.
Strict OpenSpec validation passed all 31 items. The objective documentation
baseline is empty; 30 unknown review dates remain visible and require real
scoped factual review. Local checks do not claim merged-revision CI or native
harness/Obsidian qualification.


Final local required-check run on the reviewed working tree based on `baa8629`:
all seven checks passed, including **2,028 tests passed and 8 skipped** in
301.56 seconds. The receipt correctly reports a dirty working tree; this is
local pre-commit evidence, not an exact merged-CI receipt. After recording these
results, only this record, the task checklist and content-bound documentation
disposition were updated; source and tests were unchanged.
