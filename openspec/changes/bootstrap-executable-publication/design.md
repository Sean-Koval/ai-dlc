## Decision

Use one unique staging directory under the bootstrap bin directory, so executable
replacement is on the same filesystem. Extract the verified uv archive there.
Prepare executable mode, then move each complete uv/uvx file into bin by basename.
Stage a copy of the verified cached mise file there before publishing it too.
Reject unexpected installed destination types. Do not copy/chmod installed images.

The existing download helper uses a unique same-directory temporary file per
invocation and checks its digest before rename. Helpers run in subshell scope so
caller variables/traps and concurrent invocations remain independent.

Retain extraction/staging directories and failed download files, reporting known
paths. Never recursively remove them or check a pathname then delete it. Successful
uv/uvx publication moves the binaries out, so normal stage residue consists of
archive metadata/empty directories. Failure may retain larger files. Manual
inspection and removal is explicit; no cleanup by filename pattern.

## Limits

Cooperating bootstraps sharing owned runtime locations are the target. This is
not an adversarial-filesystem guarantee, an atomic uv/uvx/mise group update, shared
venv serialization, global CLI symlink selection isolation or crash durability.
Existing source/release routing, pins, platform choice and environment names stay.
No native executable stall is deliberately reproduced. The observed macOS UE
state has no established causal diagnosis; separate host evidence is required.

## Verification

Drive the real script with an isolated pinned fake archive and held old descriptors.
Coordinate overlapping fake downloads through explicit process barriers, not a
stress timing assumption. Inject pre-publication failures and replaced stages.
See the [plan](../../../docs/superpowers/plans/2026-09-07-bootstrap-executable-publication.md).
