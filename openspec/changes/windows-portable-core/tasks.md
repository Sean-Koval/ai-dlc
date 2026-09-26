# Authoritative implementation tasks

Implementation authorized on September 26, 2026 after publication of the reviewed specification. Checkboxes record verified implementation; actual platform evidence is recorded separately.

## 1. Baseline and contract

- [ ] 1.1 Audit core CLI/MCP imports and write/command call sites listed in design.md; record retained Unix behavior and the local NTFS/Windows 11 x64 boundary against WPC-01/WPC-03.
- [ ] 1.2 Implement one validated command union for setup, verify and checks, including malformed-input preflight, original config digest binding and schema-4 compatibility tests (WPC-04; amended PC-01).
- [ ] 1.3 Add direct argv and explicit `posix`/`powershell` execution to the existing runner; test literal argument preservation, `.cmd`/`.bat` refusal, missing shell/executable, cancellation and no implicit downloads (WPC-05/WPC-06).

## 2. Safe native storage

- [ ] 2.1 Isolate Unix dependencies and implement the Windows private-account/handle-based lock backend, normalized project identity, nesting and cross-process release (WPC-01/WPC-02).
- [ ] 2.2 Implement native containment, reparse/identity checks and safe staged write/create behavior in responsible helpers; adapt direct callers without weakening Unix protections (WPC-03).
- [ ] 2.3 Verify ownership, stage-swap, junction/ancestor-race, case-alias concurrency, killed-holder, existing-destination and sharing-violation scenarios on actual Windows; report unavailable cases explicitly (WPC-02/WPC-03/WPC-07).

## 3. Existing service integration

- [ ] 3.1 Route setup verification/retry and dependency markers through the portable contract, including `.venv/Scripts/python.exe`, invalid steps before mutation and changed-input rerun (WPC-06).
- [ ] 3.2 Exercise generic adoption/render and CLI/MCP checks through shared services on Windows with POSIX tools absent; preserve authored content, credential boundaries and generated-file conflicts (WPC-01/WPC-06).
- [ ] 3.3 Extend required/focused receipt tests for argv/script records, failed/missing/cancelled checks, dirty state and unchanged trusted completion requirements (WPC-06; amended PC-01).

## 4. Review and evidence

- [ ] 4.1 Run native Windows integration cases and relevant existing Unix compatibility/security tests; classify fixtures, actual OS behavior and absent live-client evidence separately (WPC-07).
- [ ] 4.2 Review/update architecture, framework delivery design, release verification and downstream workflow command examples; enroll any justified durable document and record documentation-impact/content-bound dispositions only for required targets.
- [ ] 4.3 Validate this named OpenSpec change strictly; run prepared `ai-dlc project check --required` and resolve review findings without claiming downstream bootstrap or desktop qualification.
- [ ] 4.4 Complete specification/work-record and affected-document review, record required content-bound dispositions, strictly validate this change, run the prepared required checks, and resolve actionable review findings.

## Subsequent delivery gates

After implementation and the checklist above are complete, archive this independently owned change on its bound delivery branch with `ai-dlc work archive`. Repair moved artifact links and any evidence targets actually made stale by archival. Immediately before authorized merge, update from the target branch and refresh required checks/evidence. Finish through `ai-dlc work finish` against the exact merged revision and its configured receipts. These remain mandatory later delivery gates, not checkboxes that must falsely claim post-merge completion before archive. No package publication or paid comparison is authorized by this task list.

## Execution interfaces and focused verification

- Command parsing and execution live in `src/ai_dlc/setup/commands.py` and `project.py`; the existing `run_command` service remains the setup/check entry point. Run `python -m pytest tests/test_portable_commands.py tests/test_checks.py` after the red/green command cases.
- Native storage lives in private `src/ai_dlc/_windows_storage/`; shared `files.py` and `locking.py` retain their public APIs. `safe_read`, `guarded_path`, `atomic_publish` and handle-bound `move_owned` are the native integration boundary. Run `python -m pytest tests/test_windows_storage.py`; Windows-only cases must execute in the native CI job.
- Document adoption calls `document_files.create_document`; renderer and template recovery preserve snapshots and intervening edits. Run `python -m pytest tests/test_windows_document_dispatch.py tests/test_windows_render.py tests/test_template_recovery.py tests/test_windows_core.py`.
- Core imports must not import Unix-only modules eagerly. Run `python -m pytest tests/test_portable_imports.py tests/test_knowledge.py tests/test_hooks.py`.

Review focus: missing or malicious command records before setup effects; literal metacharacter/empty argv; case aliases and killed lock holders; reparse/ancestor substitution and private namespace ownership; failed publication or recovery racing an authored replacement. Pin these cases in the owning tests before implementation. Run the prepared required checks and native CI after integration; a local platform skip is not a passing Windows observation.
