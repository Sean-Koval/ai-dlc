Task 0 is the completed bootstrap record: it creates the reviewed work record and
this OpenSpec change from the approved [detailed design](../../../../docs/superpowers/specs/2026-09-03-portable-profile-enrollment-design.md).

## 1. Portable credential declarations and machine bindings

- [x] Add schema-4 personal credential requirements and machine environment-name bindings, including redacted readiness reporting and legacy `token_env` normalization.

## 2. Enrollment locks and XDG paths

- [x] Model schema-1 enrollment locks, XDG-owned paths, validated machine IDs, and atomic lock/machine-file persistence.

## 3. Verified Git profile cache

- [x] Resolve local or Git sources to exact commits, validate secret-free profile content, and materialize an immutable digest-verified cache.

## 4. Enrolled configuration resolution

- [x] Discover enrolled personal and machine files automatically with base → personal → project → machine precedence and compatible explicit overrides.

## 5. Preview-first enrollment services

- [x] Implement enrollment, legacy migration, and read-only status with candidate previews, lock-last activation, and redacted readiness.

## 6. Reconcile, sync, and diagnose

- [x] Compose planning, apply, deliberate sync, and doctor services so candidate failure preserves the active lock and client ownership safeguards.

## 7. Machine CLI lifecycle

- [x] Add thin `machine` CLI commands and retain compatible setup, profile, doctor, and explicit path entry points.

## 8. Portability and containment proof

- [x] Prove two-machine isolation, offline cache use, transaction rollback, authored-client preservation, and absence of credential values end to end.

## 9. Public example and durable guidance

- [x] Ship a nonpersonal profile example and update product, migration, architecture, workflow, and generated-template guidance.

## 10. Dogfood and release-grade review

- [x] Validate the dogfood lifecycle, run required gates, record factual verification evidence, complete independent task reviews, and archive the completed change.
