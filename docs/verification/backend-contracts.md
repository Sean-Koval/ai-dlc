# Backend contract verification

On September 14, 2026, source-generated Python and Node projects were initialized
with the optional backend capability and prepared through project setup. The
checks used openapi-spec-validator 0.7.2 and Redocly CLI 1.34.16 respectively.

Both projects passed their required checks with offline tool execution and HTTP
and HTTPS proxies pointed at an unavailable local port. Python passed all five
checks, including the absent-app drift skip; Node passed all four checks. Replacing
the contract with malformed YAML made each real validator fail with parsing
diagnostics. The Node generated-file check remained clean with the malformed
contract, and a valid project-authored contract title edit passed all four checks.
Setup had populated the tool caches beforehand; this does not establish
installation without a network or operation from empty caches.

Nine automated scaffold and drift cases cover all four presets, capability
omission and provider-role composition, pinning, catalog enrollment, absent and
other-framework apps, direct FastAPI instances, re-exports, factory-created apps,
readable differences, unchanged contract bytes and broken imports. The FastAPI
cases use a bounded substitute for its schema-export surface. They establish
drift-script behavior, not qualification of a live application or deployment.

The [greenfield workflow](../workflows/greenfield.md) describes project use;
[BE-01 and BE-02](../../openspec/specs/backend-capability-pack/spec.md) define the
contract. Local execution receipts are disposable evidence and are not packaged
with generated projects.
