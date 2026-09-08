# Setup continuity on native macOS and Ubuntu

Observed source: clean `189913b6cfc2c42828e35f4e2755c982b7f1e2da`, September 8,
2026. These are actual CLI/Git/filesystem observations on disposable projects.
They extend #14/#17 evidence; they do not complete either issue.

The same [frozen probe](setup-continuity-189913b/probe.py) ran on macOS 15.3.2
arm64 and Ubuntu 24.04.3 aarch64. Each used independent temporary project,
profile, bundle and XDG directories, with the already prepared Python 3.12.11
interpreter. The native host and Linux container/environment were reused; no
factory-clean or new bootstrap claim follows. The container's bridge was
disconnected before execution and inspection confirmed no attached networks
afterward. Native networking was not blocked at the OS level.

| Observation | Native and container result |
| --- | --- |
| Repeat adoption, profile enrollment, render and check | Exit 0; project and local configuration snapshots unchanged byte-for-byte |
| Update selected bundle v1 to v2 | Exit 0; previous bundle retained at the reported backup path |
| Invalid bundle payload hash | Exit 2; whole project snapshot unchanged |
| Authored modification to a managed skill | Render refused, exit 1; authored bytes and whole project preserved |
| New render processes after original sources were renamed away and cache emptied | Exit 0; Codex and Claude skill bytes match pinned v2 |
| Offline readiness | Exit 1; account/repository/vault settings remain missing; container PATH also lacks some selected tool requirements |

Import and selection are separate: the probe explicitly selects the imported
bundle in its disposable configuration. The reserved HTTPS bundle URL uses a
recorded task-local Git rewrite to a local file repository, with file-only Git
protocol. This tests actual bundle handling and consumption, not remote source
portability. Profile and bundle commits are independently recorded per environment.
The operator restored only its deliberately appended conflict marker after proving
refusal; no user-authored application or vault was involved.

## Evidence and limits

The [structured report](setup-continuity-189913b/report.json) records three
observations per environment: repeat setup, authored preservation and offline
restart. [Native captures](setup-continuity-189913b/native.json) and
[container captures/context](setup-continuity-189913b/container.json) preserve
command arguments, exit status, timestamps, durations, stdout/stderr and snapshots.
Literal machine/source/workspace paths are redacted; report hashes authenticate
these redacted artifacts. The probe source is unchanged. Generic probe labels do
not establish container identity: its actual inspection record supplies that
context. Input content is synthetic, while the CLI operations are real.

The first three native attempts stopped on probe setup mistakes: local-path
bundle syntax, omitted explicit bundle selection, and an assumed existing agents
table. Their raw evidence is retained locally; they are not passing runs. The
fourth native attempt and first container attempt completed all probe steps.
No product repair was needed for these probe corrections.

Hash/structure validation succeeds and explicitly reports Q-01, Q-02 and Q-03
unmet. Complete configured setup and a failure during staged publication were not
exercised; invalid-hash refusal occurs before publication. Actual two-provider
cycles, fresh native-client handoffs, work-laptop accounts, human evaluations and
release gates remain separate. Rendering Claude/Codex files does not verify an
actual Claude, Codex or Antigravity session.
