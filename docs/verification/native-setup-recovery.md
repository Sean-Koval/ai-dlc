# Native repeat bootstrap and controlled update recovery

Two additional native observations passed at source revision
`189913b6cfc2c42828e35f4e2755c982b7f1e2da` on Darwin 15.3.2 arm64. They cover
repeat source bootstrap and one controlled bundle publication failure followed by
recovery. They do not complete Q01–03, account or vault readiness, container
coverage, or fresh native model-client qualification.

The [report](native-setup-recovery-189913b/report.json) references redacted
[bootstrap captures](native-setup-recovery-189913b/bootstrap.json) and
[recovery captures](native-setup-recovery-189913b/recovery.json). Each artifact
includes the exact historical probe text after disclosed path redaction, raw
capture hashes, commands, outcomes and filesystem hash snapshots. The probes are
historical evidence, not a supported execution interface. No production source or
failure hook was added.

## Repeat source bootstrap

The operator created a clean disposable sparse clone at the reviewed revision,
excluding historical tracked `target` build outputs to limit disk use. It had
1,803 present tracked files. Existing pinned download artifacts, Python and mise
tools were copied with APFS clone semantics into task-specific directories. An
existing prepared environment was also copied, and the existing uv artifact cache
was reused with offline mode. All XDG and mise state/configuration directories
were isolated; no actual user provider settings were configured or called.

Both actual invocations of `sh scripts/bootstrap.sh --source` exited 0 and
reported `ready=true`, agent configuration `clean=true`, and `changed=[]`.
The first invocation reported both setup steps `completed`; the second reported
both `unchanged`. All 1,803 present tracked file hashes matched before and after
both runs, and the disposable clone and original source remained Git-clean.
These observations supplement the earlier adopted-project enrollment/render
continuity evidence; they do not change the earlier repeated adoption's logical
conflict result.

Runtime preparation did write local runtime/cache state: uv recreated environments
and installed packages from the cache. The initially seeded checkout `.venv`
symlink became a separate checkout environment alongside the bootstrap source
environment. The second bootstrap therefore is not evidence of zero runtime
writes. Two extraction directories were deliberately retained, as required by the
bootstrap preservation design; this is not duplicate generated project content.
No runtime downloads were needed. Offline flags and cached inputs do not establish
an OS-wide network boundary or factory-clean setup.

## Controlled staged update and recovery

A separate disposable generic project received an operator-authored local Git
bundle with 500 template files. Its initial revision was
`3f86be26f5c7f1e442857e99e407a1a921f81229`; the reviewed update was
`8472f9d393b6affcfc3c153403b9abf7e951e6c9`. A reserved HTTPS source identifier
was routed to local Git with a task-specific rule and file-only protocol. No
remote provider or source was contacted.

During the actual update CLI process, the operator observed the real backup
rename and stopped only that owned process. The active path was absent; snapshots
confirmed that the backup matched all previous active bytes and the complete
stage contained the new payload and metadata. The operator set the macOS
user-immutable flag on the staged directory, then resumed the process.

The update exited 2 with `bundle filesystem operation failed` and an explicit
retained-stage diagnostic. The original active bundle was restored byte-for-byte.
All preexisting project file bytes were preserved; only the retained 502-file
stage was added. This exercises failure after backup movement with successful
restoration, beyond the earlier invalid-hash refusal before staging. No syscall
trace was captured, so no captured errno is claimed. It is a controlled local
filesystem fault, not a spontaneous production failure.

The operator then removed only the flag it had applied, preserving every path,
and retried the same pinned update through the CLI. The retry exited 0 with
`applied=true` and installed the reviewed v2 lock and payload. The prior failed
stage remained byte-identical; the successful update also retained its old-bundle
backup. No installed-tree drift, backup-identity replacement, incomplete
restoration, or Linux failure path was exercised by this observation.

## Evidence, review and retained resources

Raw evidence remains in ignored `.ai-dlc/local/q01-native-extra-189913b` in the
source checkout. The original bootstrap probe SHA-256 is
`48cc46f3accf76c21b71694a18a57d334b5e8970aa097aaf75192ca3cdf0bc86`;
the original recovery probe SHA-256 is
`6df6c8aea5ac841972a6557a91e9472bf3b757b3aedb5d8b1c720020de3f9dcf`.
Packaged probe text has path replacements and therefore differs from those raw
bytes. Artifact hashes in `report.json` identify the packaged bytes instead.

Redaction replaces the source/evidence/prepared-runtime roots, user home/name,
abbreviated source root and host temporary root in every string and key, including
command arrays and metadata. Parsed JSON is reserialized; timestamps, outcomes,
numbers, file hashes and revision pins remain unchanged. The packed
`observed_summary.host.inherited_python` identifies the later snapshot collector;
the actual CLI executable paths and bootstrap interpreter selection are recorded
in their command captures. Reviewers must assess provenance and meaning: hashes
and structural validation alone cannot authenticate live observations.

The report validator passed structurally with `live_authenticated=false`,
`qualification_complete=false`, `human_review_required=true`, and Q01–03 unmet.
A separate comparison checked 92 packed capture/probe items against the retained
raw originals under the disclosed redaction, and the existing distribution
privacy predicate passed for all four added files against native and container
source-root patterns. No full build or test suite was run for this evidence-only
change.

After independent review, inspect the task-owned `bootstrap` and `recovery`
subdirectories before removing them. They contain the disposable clone, isolated
runtimes and XDG data, local bundle repository, failed stage and successful-update
backup. The operator's immutable flag is already cleared. Preserve the packaged
captures and raw evidence until the coordinator authorizes cleanup; do not remove
the inherited prepared runtime or shared uv cache. No container was used or
modified, and no full test suite was repeated for this documentation change.
