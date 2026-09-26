# windows-portable-core Specification

## Purpose
TBD - created by archiving change windows-portable-core. Update Purpose after archive.
## Requirements
### Requirement: WPC-01 Native core imports and bounded platform support
The core CLI and MCP services SHALL import and support local project adoption, managed rendering, setup and checks on Windows 11 x64 with local NTFS using installed supported prerequisites, without importing Unix-only modules unconditionally, requiring a POSIX shell for native argv commands, or requiring WSL, administrator rights or Developer Mode. Existing supported Unix behavior SHALL remain compatible. Unsupported native filesystem/architecture boundaries SHALL be explicit before mutation.

#### Scenario: Native interpreter opens the core services
- **WHEN** the CLI and MCP project-service imports and a generic adoption/render operation run on Windows 11 x64 with no `sh`, WSL or Unix Python modules available
- **THEN** imports succeed and supported operations complete through shared services without a POSIX helper
- **AND** authored configuration and machine-local credentials remain preserved

#### Scenario: A native operation targets an unsupported location
- **WHEN** a protected write targets a UNC/network volume or another filesystem outside the initial local NTFS contract
- **THEN** the operation refuses before mutation with the unsupported boundary and local supported alternative identified

### Requirement: WPC-02 Native locks preserve identity and exclusion
Project write locking SHALL serialize competing writers for the same project on Windows using current-user ownership, validated private namespace and native OS locks. Equivalent case/path aliases SHALL use the same lock identity. Nested calls in one thread SHALL work, unrelated threads SHALL NOT enter a held protected section, and process termination SHALL release the lock. Unsafe namespace or opened-file identity changes SHALL refuse entry without weakening existing Unix ownership/symlink checks.

#### Scenario: Two processes write through case aliases
- **WHEN** two Windows processes request a lock for paths differing only by case to the same project and the first holds its critical section
- **THEN** the second cannot enter until the first releases, and the final managed file is a complete serialized result

#### Scenario: A lock namespace is redirected or shared
- **WHEN** a lock namespace or file is redirected by a junction/symlink, has unsafe ownership/access, or changes identity during opening
- **THEN** the lock refuses and no project write runs under a falsely trusted lock

#### Scenario: A writer crashes and another retries
- **WHEN** a native process is terminated while holding the project lock
- **THEN** a subsequent process obtains the released OS lock without deleting an unverified pathname
- **AND** same-thread nested acquisition remains usable after ordinary exception cleanup

### Requirement: WPC-03 Portable writes preserve content and trust boundaries
Managed native writes SHALL reject root escapes, device/drive-relative paths, alternate data streams and unsafe reparse redirection, and SHALL validate opened object identity rather than substituting unsupported Unix flags with no protection. Writes SHALL stage complete bytes on the destination volume and preserve create-only, conflict and ownership boundaries. Failure/recovery SHALL preserve previously installed bytes and intervening authored occupants; cleanup SHALL NOT delete a staging pathname whose identity no longer belongs to the operation. Existing Unix permissions and open-reader replacement behavior SHALL remain intact.

#### Scenario: A valid native path contains spaces and Unicode
- **WHEN** an owned file is updated in a local NTFS project path containing spaces and non-ASCII characters
- **THEN** readers see a complete old or new file and the write stays inside the intended project

#### Scenario: An ancestor is replaced by a junction
- **WHEN** a managed destination or ancestor is redirected before or during publication
- **THEN** the operation refuses without writing into the redirected target or deleting the replacement occupant

#### Scenario: Publication is blocked by an open handle
- **WHEN** Windows denies replacement because an existing target is open without compatible sharing
- **THEN** the prior bytes and installed selection remain usable, the failure names the blocked operation, and retry after closing the handle can succeed

#### Scenario: Recovery encounters authored content
- **WHEN** create-only publication finds an existing destination, or failed staging/rollback encounters an independently changed object
- **THEN** it preserves that object and reports conflict or retained staging for inspection instead of replacing or deleting it

### Requirement: WPC-04 Minimal compatible command records
Project setup commands, optional verification commands and check commands SHALL accept either a nonblank legacy POSIX string, an exact `{argv: nonempty string list}` record with nonblank executable, or an exact `{shell: posix|powershell, script: nonblank string}` record. Command fields SHALL reject NUL, invalid types, mixed/unknown keys and unknown shells before runtime resolution or child launch. Empty argument strings after argv[0] SHALL be allowed. Setup SHALL preflight all step command shapes before its first mutation. Focused check selection and required-definition validation SHALL retain their existing ordering and preflight guarantees.

#### Scenario: A repository adopts native argument commands
- **WHEN** a schema-4 project provides valid argv records for setup, verify and a selected check
- **THEN** the new engine accepts each through the same command parser and retains their check/step IDs

#### Scenario: Command forms are ambiguous or malformed
- **WHEN** a command mixes argv and script, uses an unknown shell/key, contains NUL or has an empty/nonstring executable
- **THEN** preflight fails concisely without executing a command or writing a new execution receipt
- **AND** a malformed later setup step cannot leave earlier setup steps newly applied

### Requirement: WPC-05 Shell choice and arguments are explicit
Native argv SHALL execute without a shell using the project working directory and controlled runtime PATH/environment. Windows executable lookup SHALL support `.exe` and preserve literal arguments, and SHALL reject `.cmd`/`.bat` argv targets with explicit-shell guidance. Legacy strings and explicit `posix` scripts SHALL run only through `sh -c`; explicit `powershell` scripts SHALL run through Windows PowerShell 5.1 `powershell.exe` without profile, interaction or execution-policy bypass. Missing selected shells SHALL fail explicitly; the service SHALL NOT translate scripts, substitute shells, launch WSL or download a runtime during checks.

#### Scenario: Arguments contain shell-looking text
- **WHEN** a native executable receives argv arguments containing spaces, Unicode, empty strings, `$`, `&`, quotes and newlines
- **THEN** it receives those literal argument values without shell expansion or an extra command running

#### Scenario: Legacy POSIX syntax runs on native Windows
- **WHEN** a project selects a legacy shell-string check on Windows without `sh`
- **THEN** execution fails with the check ID, required POSIX shell and explicit migration/remedy guidance
- **AND** it does not reinterpret the string as PowerShell or claim the check passed

#### Scenario: A project explicitly chooses PowerShell
- **WHEN** a PowerShell record runs a script that propagates a deliberately failing native executable's exit status
- **THEN** the runner returns that failure through the normal check result without profiles or an execution-policy change

### Requirement: WPC-06 Runtime, recovery and evidence semantics survive portability
Setup retries SHALL verify completed work against current declared inputs and platform-correct environment markers, and rerun stale or absent work. Checks SHALL preserve existing configured-runtime resolution, no-auto-install policy, timeout/interruption classification, selected ordering, required IDs, original configuration/environment digests, revision and dirty-state bindings. Missing executables/runtimes, skipped, failed or cancelled checks SHALL NOT create successful completion evidence. CLI and MCP SHALL use the same service behavior.

#### Scenario: A native Python environment disappears
- **WHEN** a previously successful setup is retried after `.venv/Scripts/python.exe` is removed or declared dependency/command inputs change
- **THEN** the completed-step marker does not conceal drift and setup reruns or reports the failed prerequisite

#### Scenario: Required evidence is incomplete
- **WHEN** a native focused check passes but another required check is missing, failed or cancelled
- **THEN** existing completion validation rejects the incomplete receipt even if the selected command exited zero

#### Scenario: Runtime resolution or execution fails
- **WHEN** the selected runtime/executable is missing, or a native command times out or is interrupted
- **THEN** the result is non-success with the applicable reason, cancellation stops subsequent execution as before, and no check or runtime is silently installed

### Requirement: WPC-07 Platform evidence remains explicit
Acceptance of the portable core SHALL include actual Windows-process tests of imports, command arguments, lock exclusion/recovery and safe file publication, alongside retained Unix regression tests. Fixture-only, skipped safety scenarios and desktop-client outcomes SHALL be reported distinctly and SHALL NOT establish live Windows consumer or installed-client qualification.

#### Scenario: Native integration tests run
- **WHEN** maintainers record portable-core acceptance
- **THEN** the evidence identifies Windows version/architecture/filesystem, tested revision, native test commands and actual outcomes, with POSIX tools absent for the native journey

#### Scenario: A security or desktop case remains unobserved
- **WHEN** a reparse-point test is skipped or no installed-client walkthrough occurred
- **THEN** the report names the missing case and does not count a mock or passing Unix suite as its successful qualification

