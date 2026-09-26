# P0: Make core project services safe and usable on native Windows

## Problem and goal

Windows teammates cannot reach the project workflow because core imports, locking and command execution assume Unix. A PowerShell wrapper alone would hide these barriers. Deliver the existing adoption/render/setup/check service path on Windows 11 x64 local NTFS, with native arguments and unchanged content, credential and evidence protections. Product authority: [product direction](../../../docs/product-direction.md). Status: proposed/specification-ready work; no implementation or Windows qualification is claimed.

Priority: **P0**. Change ID: `windows-portable-core`. Requirements: **WPC-01–WPC-07**, plus amended **PC-01**. Dependencies: **none**. This is a prerequisite of `windows-native-setup` but can be delivered and archived independently. The [task artifact](tasks.md) is the implementation checklist; this issue packet summarizes outcomes rather than duplicating every task.

## Scope and non-goals

Scope: private Windows locking and safe file operations, core import portability, three minimal command forms, executable/runtime resolution, setup retry, and normal check receipt behavior. Native contract: Windows 11 x64, local NTFS, inbox Windows PowerShell 5.1 for explicit scripts; preserve supported Unix behavior. No all-provider/all-module promise, mandatory WSL, new orchestration layer, automatic shell translation, installer/provisioning, ARM64/network-share support or desktop-client recognition.

## Acceptance checklist

- [ ] Native core CLI/MCP imports, adoption/render and argv setup/check run without Unix-only modules, POSIX tools, elevation or Developer Mode (WPC-01).
- [ ] Actual competing Windows writers, path aliases, nested locks and killed-holder retry preserve exclusion; unsafe lock namespaces refuse writes (WPC-02).
- [ ] Real native containment/reparse, authored conflict, create-only, stage replacement and sharing-violation cases preserve previous/foreign bytes; Unix protections remain (WPC-03).
- [ ] Setup/check/verify share the specified command parser; malformed records fail before effects, and legacy strings retain POSIX meaning (WPC-04/WPC-05; PC-01).
- [ ] Literal argv, missing shell/executable/runtime, timeout/interruption and a deliberately failing acceptance command return truthful outcomes (WPC-05/WPC-06).
- [ ] Retry detects removed native Python environment/changed inputs, and passing focused output cannot satisfy missing required merged-revision evidence (WPC-06).
- [ ] Recorded Windows and Unix results identify revision/platform and missing cases, documentation dispositions are current, and no desktop/bootstrap qualification is inferred (WPC-07).

## Implementation sequence

1. Tasks 1.1–1.3 establish call-site scope and command parsing/execution compatibility.
2. Tasks 2.1–2.3 implement and adversarially test private locks and safe filesystem operations.
3. Tasks 3.1–3.3 integrate setup, rendering and receipt semantics through existing services.
4. Tasks 4.1–4.4 complete native/Unix evidence, canonical docs review, required checks and ordinary bound delivery gates.

## Evidence matrix

| Requirement | Current evidence to inspect | Required acceptance evidence |
| --- | --- | --- |
| WPC-01 | `src/ai_dlc/locking.py:5-8`; CLI/MCP shared-service imports | Native imports plus generic adoption/render with POSIX tools absent |
| WPC-02 | `src/ai_dlc/locking.py:34-163` | Two native processes, case aliases, nested threads, killed holder, unsafe ownership/reparse refusal |
| WPC-03 | `src/ai_dlc/files.py:69-129`; `src/ai_dlc/setup/templates.py:94-124`; `src/ai_dlc/environment/bootstrap.py:70-127` | Native NTFS failure/recovery tests and retained Unix ownership/symlink/publication tests |
| WPC-04/WPC-05 | `src/ai_dlc/setup/project.py:79-139`; `tests/test_checks.py:47-145` | Positive/negative parser matrix and actual native argument/shell execution |
| WPC-06 | `src/ai_dlc/setup/project.py:153-203,278-288,325-358` | Removed environment, changed inputs, deliberate fail/cancel and focused-receipt rejection |
| WPC-07 | Existing CI omits Windows: `.github/workflows/verify.yml:14-19` | Revision-bound actual OS report; skipped/mock/client outcomes separated |

## Open decisions and handoff limits

Implementation owner selects the minimal reviewed native API binding within the fixed handle/ACL contract; avoid a new platform framework. Actual teammate client version, original failure transcript and a desktop host are unknown and do not block this specification or service implementation. They do block any later claim of desktop-client qualification. Tests requiring unavailable native privileges remain visibly unsatisfied until a suitable test host runs them. No remote mutation or package publication is part of this issue's acceptance.
