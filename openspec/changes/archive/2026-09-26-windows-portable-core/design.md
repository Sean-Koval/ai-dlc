# Design: native platform semantics behind existing project services

## Authority and observed state

[Product direction](../../../../docs/product-direction.md) supplies the outcome and preservation boundaries. Existing [portable-development requirements](../../../specs/portable-development/spec.md) own configuration, project checks and trusted completion; [bootstrap publication requirements](../../../specs/bootstrap-executable-publication/spec.md) own download/publication safety. This design proposes an extension, not a statement that Windows support already exists.

| Observed source | Current behavior | Proposed responsibility |
| --- | --- | --- |
| `src/ai_dlc/locking.py:5-8,34-141` | Unconditional `fcntl`/`pwd`, Unix UID/mode checks, directory descriptors and `flock` | Private native backend selected lazily; equivalent account/identity and serialization protection |
| `src/ai_dlc/files.py:69-129` | Path containment, symlink check, temp files, chmod, replace and link publication | Explicit Windows path/reparse/identity behavior; preserve create-only and failure boundaries |
| `src/ai_dlc/environment/bootstrap.py:20-24,70-127` | Unix shell selection and `dir_fd`/`O_NOFOLLOW` file handling | Shared portable safe file operations; PowerShell activation content remains setup-slice scope |
| `src/ai_dlc/setup/templates.py:94-124` | Multi-file staging with snapshot comparison and rollback | Preserve snapshot/conflict checks; never restore over an intervening authored occupant |
| `src/ai_dlc/setup/project.py:46-93,101-139,153-203` | Runtime resolution and string-only `sh -c` execution | Validated command union and native executable resolution; same check/evidence semantics |
| `src/ai_dlc/setup/project.py:278-288,325-358` | POSIX environment markers and string regexes inform setup retry | Platform-aware Python markers and equivalent structured-command input binding |
| `tests/test_checks.py:47-145,321-339` | Focused selection, malformed commands, cancellation, setup retry | Preserve old fixtures and extend observable native cases |

The formal PC-01 string-only validation rule and a native command record cannot both hold unchanged. This change includes an explicit MODIFIED PC-01 delta. Existing string-based TOML remains schema 4; structured records are a backward-compatible input extension for the new engine, not a claim older engines can execute them. Generated configurations using the extension must identify a compatible engine version when delivered by the setup slice.

## Minimal command contract

Accepted values at `[checks.commands].<id>`, `setup.steps[].command`, and optional `setup.steps[].verify` are:

```toml
[checks.commands]
legacy = "python -m unittest" # POSIX sh -c, including on Windows
native = { argv = ["python", "scripts/check_tests.py"] }
explicit = { shell = "powershell", script = "& python scripts/check_tests.py; exit $LASTEXITCODE" }
```

A record has exactly `argv` (nonempty list, nonblank executable, string arguments, no NUL) or exactly `shell` and `script` (allowed shell, nonblank NUL-free script). Empty argument strings after the executable are valid. Mixed/unknown keys, invalid types and unknown shells fail validation before runtime resolution, child launch or new receipt. Validate the selected commands for focused execution and required definitions as today; validate every setup step and verification expression before the first setup mutation.

Native argv executes with `shell=False`, project root as working directory, inherited controlled runtime environment, literal arguments and the existing timeout. Resolve executables on that environment's PATH with platform suffix rules; Windows `.exe` launchers are supported. Refuse `.cmd`/`.bat` argv targets rather than allow their implicit shell interpretation; an authored command needing shell semantics uses an explicit shell record. `posix` uses `sh -c`; `powershell` uses inbox `powershell.exe -NoLogo -NoProfile -NonInteractive -Command`. PowerShell scripts own native exit-code propagation, which examples demonstrate. Do not add execution-policy bypass or arbitrary shell-path configuration. Missing shell names the selected command and remedy; no WSL launch, shell substitution, command splitting or automatic install occurs. Newline and metacharacter arguments in argv remain data.

Continue `mise exec -- <argv>` where declared, `MISE_AUTO_INSTALL=0` during checks, and UV's no-download constraints. Both setup verification and check execution use the same parser/runner. Receipts bind original command configuration including command kind and shell, environment and revision. A changed command representation changes the digest; a partial passing receipt cannot stand in for a complete required run. Missing executable/runtime produces non-success with an actionable prerequisite reason; timeouts/interruption remain cancelled, and no unexecuted check is reported passed.

No command dispatcher, new workflow DSL, automatic platform alternatives or per-command policy framework is needed. Templates can use direct argv and short repository-owned Python helpers for genuinely conditional setup behavior.

## Lock and filesystem boundary

Keep existing public helper APIs and the Unix implementation's semantics. Put Windows-only imports/FFI behind a private backend. Use Windows native handles and `LockFileEx` for cross-process exclusion; use current-user SID/DACL checks and file identity from opened handles instead of pretending Unix mode bits establish Windows privacy. Use a private per-user lock namespace under the resolved local application-data location. Never derive account identity solely from a caller-controlled `HOME` or accept a redirected/shared lock directory without validation.

Derive a project's lock key from stable resolved volume/file identity so case aliases and equivalent paths contend on the same lock. Preserve same-thread nesting and process-local thread serialization. Retain lock files; process exit releases the OS lock. Validate ownership, link count where relevant, and opened-path identity before entering the protected section. Reject symlinks, junctions and other reparse redirects in protected paths, including a raced ancestor; do not rely on `Path.is_symlink()` alone. Existing read-only consumers need not gain new write privileges.

The initial native write guarantee is local NTFS. Refuse unsupported filesystem/network-path operations before mutation with the boundary named. Implement handle-based checks/publication sufficient to make path substitution fail safely; do not copy Unix descriptor code while dropping unsupported flags. Reject drive-relative paths, alternate data streams, device namespaces and root escapes in managed relative destinations; exercise case collisions and Unicode/spaces.

Stage complete bytes on the destination volume, flush, and verify identity before publication. Preserve existing create-only behavior and authored-content conflict detection. Windows may refuse replacing an open executable or file because of sharing mode; return a retryable failure preserving old installed bytes and selection, not unlink-then-copy. Preserve Unix successful replace/open-reader semantics. Cleanup removes only an object still known to be this operation's staging object; report/retain anything whose identity changed. Multi-file recovery must not erase a writer's intervening edits. This provides existing operation boundaries, not a transaction across every project file or a guarantee against a hostile administrator.

## Compatibility, rollout and evidence

Implement the new backend and parser with Windows/Unix integration tests first; native setup consumes them later. Audit direct uses of `fcntl`, `pwd`, `os.getuid`, directory descriptors, chmod/private secrets, executable suffix assumptions, shell launch and guarded filesystem functions on the core import/adoption/render/check path. Do not claim all unrelated providers are portable because core imports pass.

Native tests must run in a real Windows process with POSIX tools hidden from PATH. Required adversarial cases include competing processes using case aliases, killed lock holder, nested locks, reparse redirection, stage replacement, existing destination on create-only, sharing violation, arguments containing `&`, `$`, spaces and Unicode, missing shells/runtime, deliberate failing check, and retry after failure. Relevant Unix cases stay green. Platform skips explicitly name privileges/features and do not satisfy the missing Windows case.

## Documentation impact and open decisions

At implementation, update the canonical documents named in proposal.md and record content-bound dispositions; do not duplicate this specification in docs. Downstream examples remain generic and preserve personal credential boundaries. Windows CI proves native service behavior only; clean consumer bootstrap and installed-client recognition belong to later evidence.

No product decision blocks this contract. Implementers must confirm the smallest native API binding/package choice within existing dependencies and record the review before introducing a dependency; native handles plus the Python standard library are the preferred baseline. Corporate filesystem restrictions and the teammate's exact shell/client build are qualification inputs, not permission to claim broader support. A test host lacking a privilege cannot establish the corresponding safety scenario by mock alone.
