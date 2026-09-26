# Backend contract verification

On September 14, 2026, source-generated Python and Node projects were initialized
with the optional backend capability and prepared through project setup. The
checks used openapi-spec-validator 0.7.2 and Redocly CLI 1.34.16 respectively.

Both projects passed their required checks with package-manager offline flags and HTTP
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

## Validator update check and combined frontend qualification

Later local review on September 14 found that Redocly CLI 1.34.16 can request an
update version when its 12-hour cache is absent or stale, even with telemetry
disabled and npm offline mode. An isolated probe loaded the installed notifier
module, forced a missing cache, cleared CI, NODE_ENV and LAMBDA_TASK_ROOT, and
substituted its fetch function so no network request was sent. The original
settings attempted one update fetch; adding
`REDOCLY_SUPPRESS_UPDATE_NOTICE=true` attempted zero. Generated Node contract
checks and tool setup/verification now supply that setting explicitly. Regression
cases verify the emitted environment for backend alone and both packs. This
probe covers the validator's update check; user-authored remote contract references
are separate behavior and were not part of this local contract fixture.

A generated Node project selecting both backend and frontend completed explicit
setup, retained both check sets and passed all five required checks with no
BASE_URL (smoke explicitly skipped). Malformed API YAML failed contract validation;
restoring the contract passed. With a local static page, all five checks passed
including real Playwright smoke. The design capture command produced PNGs and a
manifest for 1280x800 and 390x844 viewports with a visible `ready` selector. The
browser cache came from an earlier explicit `playwright install chromium`
invocation using pinned Playwright 1.58.2 during local qualification. Generated
project setup installed dependencies and the API validator, skipped browser
downloads, and reused that cache for smoke. Screenshots establish the observed
page and dimensions, not untested application interactions.

The check counts and successful missing-URL skip above describe the September 14
implementation. [Issue #169](https://github.com/Sean-Koval/ai-dlc/issues/169)
changes generated frontend smoke to fail without `BASE_URL` and adds a separate
behavioral check to new Python starters. Follow the current
[frontend procedure](../workflows/design-to-implementation.md#frontend-smoke-and-capture-evidence)
and the generated project's configured required list; these historical runs do
not establish the changed checks' results.
