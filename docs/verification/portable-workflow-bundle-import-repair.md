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
Ordinary operational failures restore prior active bytes only when the saved
backup identity/content and final restored tree authenticate. Authored changes
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

## Recovery-source identity follow-up

Independent re-review of `d4b7158` closed the original importer deletion and
false-success findings, but found a related recovery-source defect. A replaced
backup failed identity verification, yet rollback moved that same unauthenticated
pathname into the active bundle and omitted it from the recovery notes.

Six real-filesystem regressions failed before the follow-up production change:
replacement directories, in-place payload edits and new authored entries,
injected before the first backup check and immediately at the restore rename.
The repair saves previous bytes, authenticates the backup against the saved
open descriptor and those bytes, refuses restoration after known authentication
failure, and verifies again immediately before restoration. After any restore
move, it authenticates the active path before removing the backup name from the
reported set. Source/content mismatch or occupied destination reports incomplete
recovery and the known affected backup, stage/displaced and active names.

All six regressions then passed, along with all 200 importer/rendering cases.
Three additional cases mutate the source at the later pre-restore check; the
nine-case recovery-source matrix passes with authored bytes/inodes preserved.
The original accepted render-retention code and tests are unchanged.

This is destination-no-clobber recovery with before/after authentication, not an
atomic source-identity guarantee. An external replacement at the rename boundary
can be moved into the active path; post-restore authentication detects it and
requires explicit recovery, without deleting or moving it again. A known changed
source is left in place. Error notes include known affected names even when a
move has vacated one; they cannot locate a prior tree moved externally to an
unknown pathname. Stop other writers, inspect these names and any known external
moves, and preserve authored content before deliberately restoring a verified
old tree or removing residue. No automatic cleanup helper is supplied.

The follow-up `ai-dlc project check --required` passed all five outcomes:
generated, format, lint, types and test. All 1,182 tests passed in 230.50 seconds.
Strict OpenSpec validation and patch hygiene also passed. The local receipt
records dirty baseline `d4b7158`, not an exact merged-revision qualification.

A fresh `sh scripts/bootstrap.sh --source` attempt stalled while starting the
shared bootstrap uv binary on this host. The follow-up checks used the existing
prepared source interpreter with the working user-local uv 0.9.11 selected ahead
of the shared bootstrap binary, as agreed with the coordinator. Known-owned
stalled invocations were terminated; no other task's process or shared runtime
was changed to resolve the stall. This run does not claim a new successful source
bootstrap or clean-machine qualification. The preceding source preparation and
the required-check result are separate evidence.

## Delivery boundary

These are local filesystem and CLI tests. The synthetic candidate fixtures do
not claim remote Git provenance, live harness recognition, a clean-machine
walkthrough, hosted-platform verification, or merged-revision CI. Source
resolution's existing Git fixtures remain in the suite. Independent re-review,
integration, specification archive, PR/CI/merge evidence and `work finish` remain
with the coordinating task.
