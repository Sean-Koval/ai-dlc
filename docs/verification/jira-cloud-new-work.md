# Jira Cloud new-work verification

This is the bounded Jira child of [issue20](https://github.com/Sean-Koval/ai-dlc/issues/20),
not completion of its optional Plane/live-qualification scope. The formal
[JC01–06 specification](../../openspec/changes/jira-cloud-new-work/specs/jira-cloud-new-work/spec.md),
[adapter design](../design/jira-cloud.md) and [setup runbook](../runbooks/jira-cloud-setup.md)
state the supported contract and remaining inputs. No company API was contacted.

## Frozen candidate evidence, September 7, 2026

All five required checks passed via
`ai-dlc project check --required --receipt .ai-dlc/local/jira-cloud-required.json`:
generated, format, lint, types and test. The full suite reported **1,223 passed in
179.43 seconds**, including **58 new Jira cases** in provider, onboarding and
shared-workflow test files. All **17** OpenSpec items passed
`openspec validate --all --strict`.

The ignored local receipt records revision
`7252659e53f414f5826465a02455d5e7bcc683e2`, target `local`, engine `0.4.0` and
`dirty=true`. This is a frozen pre-commit candidate receipt, not clean-revision,
merged-CI, company tenant or platform qualification. The final evidence document
and task-check metadata were added after those checks; tested Python, tests,
provider metadata, guidance and runbook remained unchanged.

The candidate descends from the independently accepted common-service commit
`ab7cecbce35c3d7c2667b8227d19bbee174fb5ee`; `7252659` applies the coordinator's
`6ca7b6e` documentation sanitization/review-acceptance fix before validation.
The common-service checkout itself was not changed by Jira work.

Source bootstrap was attempted, but the shared uv executable was killed/stalled
during overlapping bootstrap publication. Only this child's stalled processes
were stopped. The child then used the existing prepared Python interpreter and
stable user uv to create its own editable `.venv`; project setup completed with
mise and both manifest setup steps. Commands explicitly placed the worktree's
`.venv/bin` and stable user tool directory before shared bootstrap tools. This
establishes a prepared local test environment, **not** successful concurrent
bootstrap or a fresh work-laptop qualification. That shared bootstrap concern
remains a separate release gate.

## Behavior evidence

The first provider flow failed before the module existed; common onboarding also
failed before its module existed. Subsequent recorded failing cases exposed lost
transition/link responses lacking read-back, absent optional search property maps,
project discovery lacking the create-permission filter, and malformed terminal or
property evidence accepted on read. Their final cases passed in the full suite.

| Requirement | Exercised evidence |
| --- | --- |
| JC-01 | Explicit bearer and scoped-token Basic headers; Cloud/site/account mismatches; foreign URL/key refusal; redirects never forward credentials; real executable provider capability response; no credential sentinel in provider failure output. |
| JC-02 | Same-request ADF/property correlation and fresh read-back; complete enhanced-search continuations; duplicate/property-marker conflicts; optional property lookup before absence; metadata/search truncation and repetition; shared journal refuses duplicate create while indexing is delayed. |
| JC-03 | Current project/type/create-field metadata; unsupported, missing, reserved and disallowed fields refused before mutation; supported scalar, ID, array and ADF values round-trip through HTTP payloads. |
| JC-04 | Current transition ambiguity and required fields; explicit route/field selection; disjoint success/cancelled resolution protection; cancelled/unknown result refusal; lost-response read-back; missing resolution and malformed property schema refusal. |
| JC-05 | Common CLI discovery/save/apply with actual local files and authored preservation; alias guide rendering from packaged assets; deterministic remote-link identity and repeated link preservation; actual WorkService PR-link flow. |
| JC-06 | Real WorkService/Registry/Journal and local files use `httpx.MockTransport`; SCM merge/CI evidence is explicitly a fixture. No live credentials, tenant mutations, native login or platform claims. |

The shared-workflow tests cover publication, start, PR linking, blocked finish
before any Jira request, successful finish, repeated finish, cancelled finish,
uncertain publication and native terminal-ID bypass refusal. Provider details stay
behind central registration; WorkService, CLI and provisioning received no Jira
branches or gate changes.

## Remaining gates

Independent Jira review is pending before integration. Actual company policy and
login, approved credential issuance/renewal, endpoint scopes, project/type access,
required custom fields, workflow validators, cancellation/success mappings, issue
linking and indexing latency are unverified. A disposable live new-issue probe
needs its own authorization and real account/service inputs. No Jira migration is
needed or implemented.

Only standard Jira Cloud issues through the configured atlassian.net site/Cloud
UUID gateway are supported. The bounded metadata subset excludes user-object and
cascading fields, subtasks, Data Center and service-management request APIs.
Complete scans may refuse at the documented request/page/resource budgets.
No atomic correlation uniqueness or exactly-once cross-machine creation is
claimed when prior publication journals/references are absent.

Optional Plane, native client authentication, PR/archive/merge, merged-revision CI
and work finish remain separate coordinator-owned scope. This child neither
published an issue nor performed any remote mutation.
