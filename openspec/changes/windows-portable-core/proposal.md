# Native Windows portable core

## Why

A teammate cannot use AI-DLC's existing project services natively on Windows merely by receiving a PowerShell installer. Imports depend on Unix modules, write coordination depends on Unix account and descriptor behavior, and every project command runs through `sh`. The product promise in [product direction](../../../docs/product-direction.md) requires the same selected workflow with explicit capability differences, independent local credentials, and preserved authored content.

This is proposed implementation scope derived from the September 26, 2026 PM review of main `3d4ffc194458d5d48aa68dc092e92b00fc443af8`. It does not claim Windows has been tested, and it does not authorize implementation or publication as part of this specification task.

## What changes

- Add a small native Windows backend behind existing lock/filesystem helpers, with Windows account ownership, handle identity, reparse-point refusal, same-project serialization and safe publication semantics.
- Make the existing CLI/MCP project-service import path work without Unix-only modules on Windows 11 x64 and local NTFS, without WSL, Git Bash, Developer Mode or administrator privileges.
- Extend existing project command values with `{ argv = [...] }` and `{ shell = "posix" | "powershell", script = "..." }`. Keep every existing string a POSIX `sh -c` command on every platform. No automatic shell translation or platform dispatch language.
- Apply that contract to setup commands, setup verification and required/focused checks; preserve runtime isolation, failure classification, setup recovery and completion receipts.
- Amend the canonical focused-check string-only validation clause to accept the new validated command records.

## Capabilities

### New capabilities

- `windows-portable-core`: native filesystem/locking/import and command-execution contracts, WPC-01 through WPC-07.

### Modified capabilities

- `portable-development`: PC-01 accepts validated native command records as well as unchanged legacy strings; focused check ordering and evidence remain unchanged.

## Scope, dependencies and exclusions

Priority: P0. `depends_on: []`. This slice is independently deliverable and archivable before `windows-native-setup`; its acceptance invokes already installed Python and test fixtures and does not require a bootstrap or installed desktop client. The future setup slice consumes this contract by change ID, not by cross-change artifact link.

Initial platform contract is Windows 11 x64, local NTFS, and inbox Windows PowerShell 5.1 for explicitly selected PowerShell scripts. Existing supported Unix behavior remains required. Windows ARM64, UNC/network filesystems, general ACL management, arbitrary shell translation, provider-specific provisioning, native desktop recognition and all-catalog Windows parity are excluded. Unsupported boundaries fail explicitly rather than disabling protections.

## Impact and documentation

Affected implementation owners: `src/ai_dlc/locking.py`, `src/ai_dlc/files.py`, `src/ai_dlc/environment/bootstrap.py`, `src/ai_dlc/setup/project.py`, and direct filesystem callers in `src/ai_dlc/setup/templates.py` and rendering/source services discovered by the bounded call-site audit. CLI/MCP remain thin callers; platform details do not move into entry points.

Canonical audience/ownership: [architecture](../../../docs/architecture.md) owns package boundaries; [framework delivery design](../../../docs/design/framework-delivery.md) owns project command and safety contracts; [release verification](../../../docs/release-verification.md) owns qualification limits; [project workflow template](../../../project-templates/project/docs/development-workflow.md.jinja) owns downstream command guidance. Update those explanations at implementation, retain documented Unix behavior, enroll any justified new durable document in `docs/catalog.toml`, and record content-bound documentation dispositions. This proposal/design/spec/tasks set owns the planned work; no new completion report is proposed.

## Planning review disposition — September 26, 2026

Reviewed against the current implementation, canonical requirements and the user's request to specify and publish the team-adoption recommendations. Scope, compatibility, dependencies and acceptance scenarios are accepted for this planning backlog. Commands and behaviors described as new remain proposed until implemented; no live platform/client qualification, release publication or paid evaluation is claimed. Implementation owner remains unassigned.
