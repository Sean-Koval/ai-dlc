# bootstrap-executable-publication Specification

## Purpose
Publish complete executable downloads through independent destination-local staging while preserving installed bytes and retaining failed stages for inspection.
## Requirements
### Requirement: BP-01 Complete executable publication
Bootstrap SHALL prepare executable bytes and permissions on the destination filesystem before replacing an owned installed executable, without modifying the previously installed object.

#### Scenario: Another process retains the previous executable
- **WHEN** bootstrap publishes uv, uvx or mise while a reader has the old executable open
- **THEN** the installed path exposes the complete executable with executable permissions and the old reader retains its original bytes and inode

#### Scenario: Staging or publication fails
- **WHEN** copy, permission preparation or replacement fails before publication
- **THEN** bootstrap fails visibly and the previous installed executable remains unchanged

### Requirement: BP-02 Independent download staging
Each download invocation SHALL use an independent temporary file, verify its configured digest before publication, and refuse invalid content without replacing an existing verified download.

#### Scenario: Two downloads overlap
- **WHEN** two invocations target the same cache destination
- **THEN** each invocation verifies its own bytes and cannot consume or remove the other invocation's staging file

### Requirement: BP-03 Non-deleting stage retention and bounded claims
Bootstrap SHALL retain and report unused or failed staging paths without pathname cleanup that could delete a replacement occupant. Source and scaffold scripts SHALL remain equivalent.

#### Scenario: A failed stage is replaced with authored content
- **WHEN** a staging operation fails after an external writer replaces its pathname
- **THEN** bootstrap preserves that occupant and reports the known staging path for inspection

#### Scenario: Publication fixtures pass
- **WHEN** local filesystem tests verify publication behavior
- **THEN** evidence distinguishes those checks from actual host startup qualification, shared environment serialization, cross-version toolset consistency and release qualification

### Requirement: BP-04 Explicit shared alias publication
Source-mode bootstrap SHALL prepare the checkout's own environment without replacing an existing working shared alias, and SHALL publish the shared aliases only on explicit request or when no working alias exists. Release-mode publication SHALL be unchanged. Each prepared source environment SHALL record the checkout it was synced from, and bootstrap output SHALL identify the checkout the shared alias runs and how to use this checkout's own environment. Source and scaffold scripts SHALL remain equivalent.

#### Scenario: A linked worktree or second checkout is bootstrapped
- **WHEN** source bootstrap runs in another checkout while a working shared alias exists
- **THEN** the alias keeps resolving to the same executable, the other checkout still gets its own prepared environment, and the output names the checkout the alias runs and the command for this checkout

#### Scenario: Publication is requested
- **WHEN** source bootstrap runs with the alias publication option
- **THEN** both shared aliases resolve to the requesting checkout's environment and the output names that checkout

#### Scenario: No working alias exists
- **WHEN** source bootstrap runs with no shared alias, or with one that does not resolve
- **THEN** it publishes the aliases so the machine has a usable executable

