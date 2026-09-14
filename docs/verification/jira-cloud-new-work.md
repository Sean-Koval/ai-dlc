# Jira Cloud new-work verification

This is the bounded Jira child of [issue20](https://github.com/Sean-Koval/ai-dlc/issues/20),
not completion of its optional Plane/live-qualification scope. The formal
[JC01–06 specification](../../openspec/changes/archive/2026-09-08-jira-cloud-new-work/specs/jira-cloud-new-work/spec.md),
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

## Independent review repair, September 7, 2026

The independent JC-01–06 review requested two corrections: required multi-select
values of `[]` passed element/allowed-value validation, and public provider
discovery omitted `jira-cloud`. The repair rejects explicit empty required
collections and null/empty/whitespace-only required ADF before plan persistence or
remote mutation, using the existing field-ID diagnostic. It keeps the unowned
issue ADF reader unchanged, preserves optional collection/ADF clears and valid
`false`/`0` scalars, and includes Jira in public builtin discovery.

Sixteen new regression cases failed before the guard/discovery repair; five
compatibility cases already passed and remain passing. The focused Jira suite
now reports **79 passed in 1.46 seconds**. All five required checks passed again,
including **1,244 tests in 297.96 seconds**, and all **17** strict OpenSpec items
passed. The ignored receipt `.ai-dlc/local/jira-cloud-review-fix-required.json`
records the frozen source/test candidate at `e377d720`, `dirty=true`, target local.
This evidence paragraph was added afterwards; source and tests stayed unchanged.
Narrow independent re-review of the repair remains pending. The live company,
platform, merged-CI and delivery limits above remain unchanged.

## Walkthrough preparation — September 14, 2026

Tracked by [issue #85](https://github.com/Sean-Koval/ai-dlc/issues/85).
The inspected engine revision is `dd05f1f1ba919d2647e46049b7cd48fbb21be1fb` (the merge of PR #131), on macOS
15.3.2 (24D81), ARM64, Python 3.12.11, AI-DLC 0.4.0. This is preparation evidence,
not a live Jira qualification. No Jira host was contacted and no Jira request,
issue, transition, PR or completion response was produced by this walkthrough.

**Stopped after preparation.** The maintainer has not supplied a disposable Jira
project, its selected provider configuration and credential environment-variable
name, or the exact approved host allowlist. No credential store was searched and
no company tenant was inferred from another ticket. The successful GitHub default
remains the qualified work tracker within its recorded scope; Jira and Plane
remain unqualified for this live cycle.

Two additional execution limits were verified against this revision:

- `ai-dlc work status WORK_ID` intentionally reports `tracker_status = "not queried
  (local status)"`. It must not be recorded as a fresh Jira read. Use the explicit
  provider read below for that observation.
- `ai-dlc provider test jira-cloud MANIFEST --live` routes to the existing sandbox,
  but its conformance entry point implements only Linear/GitHub read-only health.
  Jira live execution and all live mutation conformance are unavailable. The runner
  requires pinned test/proxy/enforcement image digests and exact `allow_hosts`;
  it cannot yet execute an arbitrary multi-step work walkthrough. Adding a reviewed
  Jira mutation target is a prerequisite to step 3 of the issue. Do not run the
  commands on the host as an isolation substitute or relabel fixture results.

### Prepared sequence (not executed)

Run this sequence only inside a future qualified runner target, using an approved
throwaway repository and Jira project. Follow the
[Jira setup runbook](../runbooks/jira-cloud-setup.md) to establish the actual Cloud
UUID, account, issue type, required fields, statuses and resolutions. Pin the
engine revision and all three runner image digests. Review every allowed host:
Jira uses `api.atlassian.com` through the Cloud UUID gateway; the configured site
identifies the tenant. GitHub PR/CI receipt retrieval may require additional exact
hosts. Capture proxy observations, and stop on an unapproved host rather than
expanding the allowlist automatically. Never mount a home directory into the runner.

1. In the throwaway Git repository, create and review
   `.ai-dlc/work/jira-qualification.toml` with schema 1, disposable scope and the
   normal specification, merged-PR and exact-revision CI gates. If no behavior is
   changed, record `requires_spec = false` with a reason; do not disable other gates.
   Commit the record. Configure `[scm]` for the throwaway repository and the actual
   receipt-producing Verify workflow. The tracker role must name the configured
   Jira provider alias, not this repository's GitHub provider.
2. Execute each command separately, retaining its exit status and redacted output:

   ```sh
   ai-dlc work publish jira-qualification
   ai-dlc work publish jira-qualification
   ai-dlc work start jira-qualification
   ai-dlc work status jira-qualification
   ```

   Compare both publish results' tracker IDs and independently search the sandbox
   project for duplicate correlation. Read back the configured in-progress status;
   local `work status` is not that evidence. From the same throwaway root, an
   explicit fresh read using the engine's provider boundary is:

   ```sh
   python - <<'PY'
   import json
   import tomllib
   from pathlib import Path
   from ai_dlc.providers.jira_cloud import JiraCloudProvider

   config = tomllib.loads(Path('ai-dlc.toml').read_text())
   work = tomllib.loads(Path('.ai-dlc/work/jira-qualification.toml').read_text())
   alias = work['providers']['tracker']
   provider = JiraCloudProvider(config['providers'][alias])
   item = provider.invoke('read', {'reference': work['artifacts']['tracker']})
   print(json.dumps({key: item.get(key) for key in ('id', 'state', 'url')}, indent=2))
   PY
   ```

3. Before a PR is merged, run `ai-dlc work finish jira-qualification`. Record the
   nonzero refusal, the specific failing gate, and a fresh Jira read proving no
   completion transition occurred. Unexpected success is a defect: stop and retain
   evidence rather than continuing.
4. Commit a harmless disposable repository change, record documentation
   dispositions if that repository requires them, and pass
   `ai-dlc project check --required`. Archive any required OpenSpec change with
   `ai-dlc work archive jira-qualification` before review. Push the bound branch,
   create the sandbox PR with `ai-dlc work pr jira-qualification`, and push the
   resulting link commit. Obtain the normal review and maintainer merge; no merge
   is authorized by this preparation record.
5. Fetch the actual merge revision into a clean checkout. Wait for its configured
   Verify run and receipts, then run `ai-dlc work finish jira-qualification` from
   that exact revision. Record the PR URL, merge SHA, run URL, receipt identities,
   successful finish and fresh Jira state/resolution. Repeat finish and verify it
   remains idempotent. If the target has moved, use a temporary detached checkout
   of the merge as documented in the development workflow.

For every numbered step, append the actual UTC time, engine/fixture revisions,
command, exit status, redacted request method/path, response status and relevant
IDs/states to this record. Include contacted hosts from the enforced proxy.
Remove authorization headers, token values, personal fields and unrelated issue
bodies before committing evidence. The absence of a response in this preparation
is **not** an observed success. Keep issue #85 and the release gate open until the
missing inputs and runner capability are supplied and the cycle actually passes.
