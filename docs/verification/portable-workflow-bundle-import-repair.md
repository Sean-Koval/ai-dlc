# Workflow-bundle importer review repair

Work: [GitHub issue 10](https://github.com/Sean-Koval/ai-dlc/issues/10).
Baseline: `21701c8`, including the independently accepted successful-render
retention repair. Full-candidate review on September 7, 2026 found two importer
defects: backup cleanup deleted authored entries/edits, and publication could
report success after stage payload or metadata drift. This report covers the
subsequent bounded importer repair. The accepted renderer remains unchanged.

## Behavior

The importer verifies the exact candidate-derived manifest, deterministic lock,
payload bytes, complete tree entries and directory identity before publication
and again after installation. Revalidating the source candidate alone cannot
authenticate a changed stage. Detected drift raises an error instead of reporting
an applied bundle with mismatched content.

Successful backups, unused/partial stages and displaced failed publications are
retained. Recursive cleanup and the reconstruction code previously needed after
partially deleting a backup are removed. Backup names are unique, so a retained
backup does not block later updates. Later imports do not adopt, modify or delete
old residue.

Publication and recovery use no-clobber directory moves. Recovery retains an
installed occupant at a new displaced path before restoring the old bundle. If
another destination blocks restoration, it is not overwritten; the failure
identifies the retained backup/stage and active destination for inspection.
Ordinary operational failures still restore prior active bytes. Authored changes
take precedence when exact original-path restoration would overwrite them.

Returned results add sorted project-relative `retained_paths` only when this
invocation leaves residue. Errors carry retained-path notes; the bundle import
CLI displays the generated notes while suppressing raw filesystem error details.
Project-root movement no longer masks the original failure's recovery notes.
Preview, an unchanged apply, and imports without residue keep their previous
result shape.

This is non-deleting retention, not atomic cleanup. It does not prevent another
writer changing content after final validation. Save the result/error output,
stop concurrent writers, inspect the exact retained files/directories, and
preserve authored or uncertain content before deliberate manual removal. Never
bulk-delete `.ID.backup-*`, `.ID.stage-*` or `.ID.displaced-*` by naming convention.
A moved ancestor can require locating the reported name in a displaced directory.

## Regression evidence

Before production changes, 23 new cases failed against `21701c8`:

- Backup new entries, in-place edits and directory replacements were deleted on
  successful update.
- First-import/update cases changed payload, manifest, lock, added content or
  replaced the stage directory immediately after staging or after installation.
  They exposed incorrect success or lost authored bytes during failed recovery.

Those cases now assert failure or success as appropriate, retained authored bytes
and inodes, exact prior active-tree restoration where safe, and discoverable
retained paths. Additional cases cover undeclared empty directories, partial-stage
write failure with authored content, later updates preserving old residue, and a
concurrent destination preventing rollback. The rollback diagnostic case first
failed because the occupied active path was omitted from the notes; it now passes.

Updating the relocated-project regression exposed another missing diagnostic:
the project-binding context's final check replaced the original error and its
notes. The test failed for missing retained-path notes, then passed after the
original error was preserved. A real CLI failure test separately failed because
exception notes were discarded; it now verifies the retained path is displayed
and a credential sentinel is absent.

Four old cases testing failures during recursive backup deletion/reconstruction
were removed because those operations no longer exist. Other cleanup assertions
now require preserved active bytes and reported residue. The existing publication
failure test injects at the replacement's no-clobber move boundary. These changes
explicitly replace the old automatic-cleanup contract; they do not pretend that
the removed destructive cleanup remains exercised.

All 193 importer/rendering cases passed before adding the CLI regression; that
new CLI case then passed independently. Strict OpenSpec validation and patch
hygiene passed.

The first broader run passed 1,171 tests and failed the distribution portability
test: the previous renderer verification note contained a machine-specific path
added after its earlier test run. The note now describes the prepared source
environment without that path. The distribution portability test and CLI
retained-path test then passed together (2 tests). A formatting-only import-order
finding in the new CLI test was also corrected before the final required run.

The final `ai-dlc project check --required` passed generated, format, lint, types,
and test outcomes, with 1,173 full tests passing in 231.03 seconds. It used this
checkout's prepared source environment. Its receipt records the dirty pre-commit
repair on baseline `21701c8`; it is local verification, not merged-revision CI.

## Delivery boundary

These are local filesystem and CLI tests. The synthetic candidate fixtures do
not claim remote Git provenance, live harness recognition, a clean-machine
walkthrough, hosted-platform verification, or merged-revision CI. Source
resolution's existing Git fixtures remain in the suite. Independent re-review,
integration, specification archive, PR/CI/merge evidence and `work finish` remain
with the coordinating task.
