# Remaining selective migration evidence

Phase1 is based on merged main189913b. PR23's actual GitHub default-only and selected mapping delivery remains credited; this change does not repeat that migration. Parent issue21 still requires a specifically chosen real Plane deployment and substitution rehearsal.

An isolated source bootstrap completed using a task-specific bootstrap directory and explicit source-specific CLI path, with Python3.12.11/AI-DLC0.4.0 on the current macOS host. This reused installed setup tools; it is not a clean-machine or native-client qualification.

## Phase1 local evidence

The existing migration/real read-identity baseline passed69 tests. New source omission/capability regressions failed twice before implementation, with the legacy schema1 compatibility case passing. A separate subprocess test reproduced FIFO saved-plan blocking at its two-second deadline; nonblocking open followed by the existing regular-file check now refuses it without reading, replacing or deleting the pathname.

New schema2 previews preserve target logical state and explicitly record unknown source state/history, omitted remote-only information and undeclared/unsupported capabilities. Legacy schema1 exact revalidation and recovery remain usable. The actual Registry and GitHub/Plane adapter matrix uses synthetic gh/HTTP transport only; Plane targets are created inside the fixture with its existing ownership contract. No source provider is invoked. Cases cover Linear→GitHub, Linear→Plane, GitHub→Plane and Plane→GitHub, default-only/selected paths, four target state classes, identity drift and unowned Plane refusal. The two non-Plane cases for the Plane-only ownership check are explicitly skipped.

Final affected results:99 passed,2 skipped in2.40seconds. Repository-wide format/lint passed; type validation reported zero errors/warnings/information. Generated render/check and asset verification passed; strict selective-tracker-migration validation and whitespace checks passed. Full required checks are deferred to the coordinator to serialize disk-intensive runs. This is not an integrated/full-suite claim.

Phase1 at7dbf445 passed independent coordinator review and was integrated as2fd14a0. Phase2 evidence follows. Independent review, required integrated checks, PR/CI, spec archive and work finish remain coordinator-owned. No real provider calls, service mutations or actual repository migration were performed by this implementation session.


## Phase2 reviewed target creation

The separate tracker_targets service and tracker-create-plan/tracker-reconcile CLI actions implement the approved explicit saved-intent design. The local work records remain untouched during reconciliation. The complete intent and destination fingerprint is validated by the existing Journal before result reuse; begin.created elects one sender. Journal initialization uses the project lock and a per-root private migration namespace to avoid a reproduced SQLite WAL initialization race. Known successful references survive read-back failures; final verification/output-save failures retain advisory targets. Local apply remains the existing separately reviewed transaction, with historical creation IDs/digest/correlations added to durable provenance.

The initial seven new service cases failed because the service was absent. During implementation, exact payload validation initially rejected the renderer's trailing whitespace; plans now store the same normalized payload accepted by the existing contract. Two explicit regressions exposed lost retained-target reporting after successful create/read-back failure and after final mapping verification failure. The CLI command test failed before the new action existed, then identified missing explicit option declarations. The real two-process test exposed concurrent WAL initialization failure before the scoped initialization lock. A non-RuntimeError transport exception and unresolved local migration each had separate failing regressions before their final recovery guards. No blind retry or remote deletion was introduced.

Actual GitHub and Plane adapters behind Registry ran against synthetic gh/HTTP transports for accepted-but-lost creation responses, invisible target reconciliation and later visibility, producing only one create. Plane retained its existing ownership and adapter-owned durable ledger requirements. Actual-adapter interrupted local-write cases retained the target and restored known local bytes. Additional cases cover saved-plan exclusivity, stale-unsent refusal, partial batches, mixed existing/created targets, full fingerprint conflicts before reads, separate apply/provenance, corrupted/symlink/FIFO intents and two competing processes. The six skips are parameter combinations where a provider-specific ownership/creation test does not apply; they are not missing live tests.

Final affected verification passed **262 tests,6 skipped in10.69seconds** across target reconciliation, migration/actual-adapter/read-identity, CLI, legacy rebind and workflow suites. Repository-wide format/lint passed. Type validation reported zero errors,warnings or information. Strict selective-tracker-migration validation, source render/check, generated assets and whitespace checks passed; the scoped work record validates with no errors.

No full required suite was run for this candidate: the coordinator requested one serialized integrated gate because of disk pressure. No real service calls, source Linear inventory, actual migration, native-client qualification or remote mutations occurred. Remaining parent scope is the specifically chosen real Plane destination/account/version and authorized substitution/interruption rehearsal, plus independent phase2 review and integrated delivery gates. Only evidence metadata changed after these checks.

## Independent review identity repair

Independent review of81c15ea found that a later correlation lookup could overwrite a previously known target ID/URL. The narrow repair compares against the current durable journal result under the project lock before publishing a result, preserves the original advisory identity on conflict, and also checks the final local plan's identity against the verified target. A state change for the same ID/URL remains allowed; conflicting lookup/read results cannot produce a local migration plan or another create.

The added regression set failed8 cases before the repair, with3 compatibility passes and2 nonapplicable provider skips. It covers changed ID or changed URL through correlation lookup, fallback read, independent read-back and final-plan verification, plus both applicable real Registry/GitHub source paths. Restoring the original fixture target proves the journal retained its original identity. The same-identity cancelled-state refresh case remains green. The repaired subset passed11 cases with2 nonapplicable skips.

Final covering verification passed **273 tests,8 skipped in24.13seconds** across target/adapter/migration/read-identity, CLI, legacy rebind and workflow tests. Repository format/lint, type validation (zero diagnostics), generated rendering/assets, strict spec validation and whitespace checks passed. Only runbook/evidence text changed afterward. No full suite or live calls were run; the coordinator integrated the repair and the scoped independent re-review accepted it with no remaining findings.

## Integrated verification

The earlier integrated candidate ccebc0f passed all five required native checks with 1,864 tests passing and 6 nonapplicable skips. After the identity repair, the focused target/adapter/migration set passed 121 tests with 8 nonapplicable skips; generated, format, lint and type checks passed, as did all 23 strict OpenSpec validations. These checks establish local behavior only. Final integrated release checks and GitHub delivery evidence are recorded by the coordinator; parent issue21 remains open for actual Plane substitution and interruption qualification.

The clean integrated revision `f6c36743b82432e9fefc9ee4344240361cf2397b` passed all five required checks in the reused Ubuntu24.04.3 ARM64 container with networking disconnected: **1,874 passed,9 skipped in225.39seconds**. The preceding Linux run at d3089fd found one packaging privacy failure in outer container-evidence paths (1,873 passed,9 skipped); the capture was redacted and rehashed without weakening the packaging guard. Independent review accepted the corrected evidence. No runtime source changed between these two checks.

The subsequent native setup/recovery evidence and release preparation are separate
slices. They do not change migration's source/target contract or fulfill the pending
real Plane substitution rehearsal.
