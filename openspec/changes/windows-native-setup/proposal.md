# Native Windows setup and consumer verification

## Why

The current source bootstrap supports Darwin/Linux, machine planning rejects Windows, and generated Python setup requires POSIX syntax. Teammates who clone AI-DLC and ask their harness to set it up therefore cannot complete the intended native Windows journey. [Product direction](../../../docs/product-direction.md) calls for reproducible selected tools and guidance with independent local credentials; a mandatory WSL detour does not deliver that outcome.

This proposal follows the September 26, 2026 PM review of main `3d4ffc194458d5d48aa68dc092e92b00fc443af8`. It is planned work, not proof of a specific terminal failure, shipped support or live platform qualification.

## What changes

- Add an equivalent native PowerShell bootstrap for Windows 11 x64 with reviewed versioned/digest-verified prerequisites and verified engine assets.
- Provision only the supported selected Windows core/Python subset; show named unsupported optional modules and unmet selected requirements explicitly.
- Support user-owned Windows install locations, executable suffixes, virtual-environment `Scripts` paths and safe PowerShell/new-terminal PATH activation.
- Make generic adoption and Python initialization/setup/render/check work without WSL, Git Bash or `sh`; keep authored POSIX commands explicit and unchanged.
- Add Windows CI and candidate/published-consumer verification with honest evidence boundaries; require a clean Windows 11 native walkthrough before Windows 11 support is claimed.

## Capabilities

### New capabilities

- `windows-native-setup`: WNS-01 through WNS-08 own the native installer, selected provisioning, activation, generated journey and platform qualification evidence.

### Modified capabilities

- `bootstrap-executable-publication`: BP-01 makes the native sharing-violation refusal explicit while retaining Unix open-reader publication behavior and preservation of previous bytes.

## Dependencies and exclusions

Priority: P0. `depends_on: [windows-portable-core]`. Consume that change's portable writes/locks and validated native argv contract; do not duplicate or replace it. This change can archive independently after the dependency is delivered. Consumer onboarding guidance may route into these services but is not a prerequisite to their implementation. Installed-client smoke qualification is a separate slice and remains an explicit unverified dimension.

Exclude ARM64, every optional catalog module, arbitrary native package managers, WSL as a prerequisite, Linux-dependent project conversion, automatic authentication, corporate policy bypass, forced administrator access, desktop-client installation/recognition guarantees and implicit package publication. Existing Unix bootstrap and legacy scaffold assets remain supported.

## Documentation impact

[README](../../../README.md) owns OS-specific entry commands and consumer/contributor routing; [work-computer setup](../../../docs/workflows/work-computer-setup.md) owns the repeatable enrollment journey; [release verification](../../../docs/release-verification.md) owns acceptance limits; [release publication runbook](../../../docs/runbooks/release-publication.md) owns the release procedure and [release candidate evidence](../../../docs/verification/release-candidate-preparation.md) records observed candidate outcomes. Review the exact current owners through [docs/index.md](../../../docs/index.md) and `docs/catalog.toml` before updating; do not create duplicate setup or completion summaries. The source and `project-templates/project/` bootstrap copies, downstream workflow guidance and packaged assets require synchronized updates and content-bound documentation dispositions. Record actual Windows evidence in its canonical verification owner only after it exists.

## Planning review disposition — September 26, 2026

Reviewed against the current implementation, canonical requirements and the user's request to specify and publish the team-adoption recommendations. Scope, compatibility, dependencies and acceptance scenarios are accepted for this planning backlog. Commands and behaviors described as new remain proposed until implemented; no live platform/client qualification, release publication or paid evaluation is claimed. Implementation owner remains unassigned.
