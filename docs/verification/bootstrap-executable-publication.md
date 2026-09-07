# Bootstrap executable publication evidence

Bounded discovered-behavior child of [GitHub #14](https://github.com/Sean-Koval/ai-dlc/issues/14), based on root `64cb09f`. Parent qualification remains open.

## Behavior and preservation

The real bootstrap stages its verified uv archive in a unique directory beneath
its own bin directory. Each executable receives mode755 before same-filesystem
rename into bin; the previously installed object is never copied over or chmodded.
Mise is copied from its verified cache into this stage before publication.
Unexpected destination directories/symlinks are refused. Independently staged
download files are hashed before replacing cache files.

The extraction cleanup trap no longer recursively deletes a mutable pathname.
Successful staging directories retain archive metadata/empty directories after
the executables have moved out. Failures may retain complete binaries, partial
files, or replacement occupants. Failed downloads retain their unique temporary
file or whatever now occupies that name. Diagnostics report known paths. Stop
other writers and inspect those exact paths before deliberately removing residue;
never bulk-delete stages by a naming pattern. Files moved externally may require
locating their new paths. This is non-deleting retention, not atomic cleanup.

## TDD and local fixtures

Baseline bootstrap tests passed (3). Before implementation, the real-script
old-descriptor case failed because copying uv changed bytes visible through an
already-open old descriptor, and two barrier-coordinated download processes failed
because one hashed the other's shared partial file. These are actual shell and
filesystem operations around pinned fake tools; no network or native process
stall is required to reproduce them.

After the repair these cases pass. Extended baseline probes separately confirmed
old-reader mutation for uvx and mise and deletion of an extraction replacement.
Final coverage includes all three executable readers, overlapping publication
from distinct stages, independent downloads, pre-publication copy/mode/rename
failures, unexpected destination types, and authored replacements after failed
extraction/download. All 15 focused bootstrap tests pass. Fixtures intentionally substitute dependency
installation, not filesystem publication. The first overlapping-bootstrap fixture
also reached the existing global CLI-link operations and one invocation failed
there. That fixture now substitutes those out-of-scope alias operations while
retaining real executable moves and stage barriers; this does not qualify the
known separate alias race.

## Actual host evidence

The updated `sh scripts/bootstrap.sh --source` succeeded with a new task-specific
bootstrap home on the existing Apple silicon host. It downloaded/installed the
pinned Python3.12.11, prepared the source environment, reported both project setup
steps complete and readiness true, and reported retained staging. The shared
bootstrap runtime was not modified. This is an isolated runtime on an already
provisioned host; existing host tools/caches and mise configuration remain inputs.
It is not factory-clean, Linux, container, remote-provider or actual-client proof.

Simultaneous earlier source bootstraps had shared uv processes observed in macOS
UE state while the user-local uv worked. The real-descriptor test establishes
in-place overwrite as a defect independently; neither it nor this successful
single source bootstrap establishes that defect as the cause of the prior stall.
Concurrent real-runtime startup remains a separate qualification.

## Scope and remaining limits

Cooperating bootstraps and owned runtime paths are the supported publication
boundary, not arbitrary hostile filesystem mutation. No atomic toolset group
update, shared source/release virtual-environment serialization, cross-version
consistency, CLI symlink last-writer isolation or crash durability is claimed.
Existing platform pins, source/release routing, environment names and workflow
services remain unchanged. Template equality is checked by the existing generated
artifact check. No new package manager or harness is introduced.

The first required run passed generated/format/lint/types and 1,198 tests, but
failed the distribution portability test because the inherited provider-connection
verification document contained a personal path. The coordinator's documentation
fix `6ca7b6e` was cherry-picked as `d4527ef`; the bootstrap repair did not introduce
or own that document. The final `ai-dlc project check --required` passed all five checks with 1,199 tests
passing in 189.84 seconds, using the task-specific source bootstrap environment.
Its local receipt records dirty baseline `d4527ef`, not an exact merged revision.
Strict child-spec validation, shell syntax, 15 focused tests and diff hygiene
also passed. Independent review and integration remain separate. Independent review, archive, integration, exact merged-revision receipts and
gated finish remain coordinator-owned delivery steps.
