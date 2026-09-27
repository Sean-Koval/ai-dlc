## 1. Reuse team-owned verification

- [x] 1.1 Add adoption-guidance cases covering an existing team test command, syntax-only checks and missing behavioral evidence; inspect `agents/skills/`, `agents/templates/`, project templates and PC-01 through PC-03 before choosing the smallest guidance surface.
- [x] 1.2 Implement the compact inspect/propose/review sequence with explicit requirement/check mapping, source citations and prerequisite decisions; preserve authored tests, required IDs and unrelated commands.
- [x] 1.3 Verify configuration changes occur only after review and normal checks neither install tools nor silently change shells; exercise existing-project preservation and non-Python projects.

## 2. Prepare and demonstrate the normal runner

- [x] 2.1 Exercise missing mise with empty tools using existing runtime diagnostics; make onboarding name the prerequisite and refuse successful evidence when no check runs.
- [x] 2.2 Prepare the source-candidate comparison runtime in the shared base for both arms using existing image preparation; run an offline candidate `project check --required` smoke without a model call, and document its image/revision identity separately from native platform qualification.
- [x] 2.3 Add a safe isolated-fixture rehearsal with initial pass, deliberate requirement regression failure and restored pass; verify fixture containment and refusal of active-checkout/production targets before mutation.
- [x] 2.4 Verify missed regressions and incomplete isolation remain unsuccessful evidence, and rerun focused/full receipt regression cases to preserve PC-01 and PC-02.

## 3. Evidence and delivery

- [x] 3.1 Execute one real local behavioral rehearsal through the normal runner and record its source/runtime identity, three outcomes and limits; do not execute paid #138 comparisons or infer quality/productivity savings.
- [x] 3.2 Review the canonical development/adoption guidance and evaluation prerequisite document; update impacted catalog mappings and content-bound dispositions without adding a parallel testing handbook.
- [x] 3.3 Complete specification/work-record and affected-document review, record required content-bound dispositions, strictly validate this change, run the prepared required checks, and resolve actionable review findings.

## Subsequent delivery gates

After implementation and the checklist above are complete, archive this independently owned change on its bound delivery branch with `ai-dlc work archive`. Repair moved artifact links and any evidence targets actually made stale by archival. Immediately before authorized merge, update from the target branch and refresh required checks/evidence. Finish through `ai-dlc work finish` against the exact merged revision and its configured receipts. These remain mandatory later delivery gates, not checkboxes that must falsely claim post-merge completion before archive. No package publication or paid comparison is authorized by this task list.


## Implementation plan

**Goal:** Reuse a team's reviewed behavior check and demonstrate its sensitivity through the ordinary runner, with a shared offline-ready comparison runtime.

**Architecture:** Extend existing task-triggered specification/delivery guidance. Keep onboarding, check execution and receipt services unchanged. Extend the existing evaluation base recipe/build path with a checksum-pinned mise binary shared by both arms; exercise the ordinary candidate runner in the existing no-model attempt smoke.

**Spec:** `specs/portable-development/spec.md`, BCO-01–BCO-05. Python/Pydantic/pytest and existing Markdown/template assets; no new dependency, service, public command, scanner or test framework.

### Global constraints and rulings

- Retain authored tests, commands, required IDs, shell contract and full receipt gates. Configuration review uses the existing authorization context; no redundant approval ritual.
- Guidance inspects exact existing sources and records unknowns. Filenames, setup success and syntax checks do not prove behavior or test adequacy.
- Checks never install tools. mise remains necessary even for empty tools; no direct-shell substitute for a failed runner.
- Rehearsal uses an explicit external disposable copy with no production inputs or remote mutations. Reject active-checkout containment and unobserved expected failure before claiming success.
- Paid #138 and native qualification remain pending. No token/productivity/quality claim follows from these fixtures.
- Ruling: extend existing `spec-from-prd` and delivery-slice guidance, rather than add an onboarding source parser or new skill. Existing planning makes no behavioral-adequacy claim; agent judgment is the appropriate source-review boundary.
- Ruling: keep optional mise metadata backward compatible in schema-1 base recipes; the shipped comparison recipe declares it explicitly. Legacy bases remain unqualified for ordinary checks until the smoke succeeds. Both arms use the same resulting base image.
- Ruling: #176 has no dependency on draft #175 and starts from completed #173/#174 main. No native-helper code is needed here.

### Review focus

Review unknown/non-Python commands without inventing mappings; focused success versus full receipts; absent mise with empty tools; wrong binary checksum/architecture; and unsafe or insensitive rehearsal. Existing runner/receipt tests and the new actual rehearsal cover these boundaries; do not add prose-string tests merely mirroring instructions.

### Task A — Compact team-check guidance

Own `agents/skills/spec-from-prd/SKILL.md`, its lock/generated copies, `agents/templates/delivery-slice.md` and packaged copy, the short project AI-DLC pointer, canonical and project-template development/brownfield guidance.

- [x] Inspect existing guidance and PC-01/02/03; add source-grounded inspect/propose/review steps, requirement/check/source/prerequisite mapping, required/optional choice and explicit unknowns using those existing surfaces.
- [x] Add the bounded external-fixture pass/fail/restored-pass procedure, isolation refusal, missed-regression failure, honest evidence fields and normal-runner mise requirement. Keep the detailed procedure in one canonical workflow and use short task-specific pointers elsewhere.
- [x] Update generated/locked copies using repository tools; preserve authored application tests/configuration. Run relevant existing rendering/template/preservation/check/runtime/receipt tests and scoped asset checks; no new scanner, service, skill or redundant textual tests.
- [x] Self-review and commit only owned files; record concise affected checks and limitations in ignored task-a-report.md for independent review.

Task A implementation `66a429e` passed independent specification/quality review; the ineffective baseline heading probe in its scratch report was corrected. Generated assets and 18 focused existing cases passed.

### Task B — Common evaluation runtime and ordinary-runner smoke

Own `verification/evaluation/contracts.py`, `image.py`, generated base-image schema, shipped `evaluations/images/claude-code.json`, `tests/test_evaluation_base_image.py`, `tests/test_evaluation_attempt.py`, evaluation README and canonical evaluation record (preparation instructions only; controller owns actual evidence later).

- [x] Add failing contract/build tests for optional strict mise version/platform hashes, absent architecture and checksum mismatch, exact executable bytes/mode in shared base, and offline non-root version check. Preserve recipes without the optional block; state their runtime limitation.
- [x] Add checksum-pinned mise to the shipped shared base recipe using the existing bootstrap Linux x64/arm64 pins and existing HTTPS fetch pattern. Verify architecture/digest before build, no extra runtime installed by candidate checks. Record mise identity in build output when declared; no paid model call.
- [x] Update the existing no-model candidate attempt smoke to run `project setup` and `project check --required` with a collected receipt under its existing offline isolation, while baseline receives no AI-DLC guidance. Retain direct behavioral test evidence separately; assert actual required outcomes, not just exit/version text.
- [x] Repair the observed raw local-image ID handoff using a verified content-derived local alias while preserving the digest-bound input/result and ancestry checks; refuse alias conflicts and retain the underlying baseline image. Cover local/matching/conflicting references and failed identity checks.
- [x] Regenerate the schema, run focused image/attempt/schema tests and scoped Ruff/types, self-review and commit owned files. Do not launch real builds: controller runs and records those after the code is clean.

### Task C — Actual rehearsal, verification and delivery

Controller owns ignored execution/evidence, catalog/dispositions and these specification tasks.

- [x] Use an external disposable copy of the committed CSV fixture. Record source/tree/runtime identities, one reviewed column-count requirement and authored unittest command; run focused pass, introduce only the reviewed behavior regression in the copy, require observed failure, restore exact bytes and require pass. Record isolation-refusal and undetected-regression controls; preserve active checkout and user content.
- [x] Build the common base and candidate on available Linux arm64 Docker, then run the no-model offline ordinary-runner smoke. Record exact image/wheel/source/receipt identities, separate from native or paid comparison evidence.
- [x] Record reviewed canonical evidence/catalog mappings and content-bound dispositions; validate specification/work records and run required checks. Obtain task reviews then whole-branch review; resolve findings.
After the implementation checklist: archive this independently completed specification, push/PR, refresh against target, merge only after required checks, and finish from exact merge with configured receipts. No package publication.

Final implementation verification at `17988aa`: all eight required checks passed on a clean tree; 3,179 tests passed and 40 skipped. Independent whole-branch review found only a documentation anchor issue, resolved and independently reviewed in `54c6284`. Later archive/link metadata is rechecked separately and hosted checks must cover the final delivery revision.
