# Portable profile enrollment review record

## Status and review basis

This record catalogs the independent task reviews completed during implementation of
the approved [portable profile enrollment design](../superpowers/specs/2026-09-03-portable-profile-enrollment-design.md)
and [implementation plan](../superpowers/plans/2026-09-03-portable-profile-enrollment.md).
The branch starts from `b256acd` and the last reviewed Task 9 revision is `6c490f4`.
Task briefs, implementation reports, review diffs, findings, fix rounds, and re-review
outcomes are retained in the ignored SDD execution ledger.

The complete branch through Task 10 was independently reviewed across
`b256acd..5c3e885`. That review found four Important gaps and one Minor documentation
gap. A subsequent re-review confirmed the four original behavioral findings were fixed
and the documentation correction was present, but found a compatibility regression in
the sensitive-field normalization. The bounded adjudicated correction below is locally
verified; independent approval of that correction remains pending.

## Completed independent task reviews

| Task | Reviewed revisions | Findings and disposition |
| --- | --- | --- |
| 0 — records and OpenSpec | `b3065ae`, `262fde4` | One Important capability-delta finding was corrected; re-review was clean. |
| 1 — credential declarations | `96f1796` | The only objection conflicted with the plan's required `source` field; the recorded ruling retained the non-secret resolver identity with no code change and no open finding. |
| 2 — enrollment persistence | `dac852c`, `917e026`, `23efda6` | Atomic machine creation, a real lock-replacement failure boundary, warning-free schema serialization, and the public `schema` contract were corrected; re-review was clean. |
| 3 — verified Git cache | `ee4718c`, `2dba762` | Unadvertised pseudoref, raw-SHA, wildcard, and refspec acceptance was closed; re-review had no open correctness finding. |
| 4 — runtime resolution | `b7de50b`, `bcd4826` | Explicit personal replacement no longer verifies the replaced enrolled cache while inheriting the machine scope; re-review was clean. |
| 5 — enrollment services | `0352ebe`, `4ccd52e`, `9a60db0`, `7f7330e`, `2ac97e6`, `e579e23` | Review rounds corrected source redaction and grammar, lock-last result construction, ownership-error classification, stable portability, default modules, and ambiguous Git syntax. The final cwd-shadow source-identity correction was explicitly carried into Task 6. |
| 6 — reconcile, sync, doctor | `c6e7b31`, `3466c74`, `96c7fa8`, `28eac5d` | The carried source-identity issue and findings in error redaction, Linear readiness, degraded doctor behavior, legacy sync, and explicit environment isolation were corrected; re-review was clean. |
| 7 — CLI lifecycle | `169e386`, `9c5dc2e`, `474d1c3` | Reviews corrected matching-scope overrides, `--home` forwarding, root-doctor help, and explicit-machine readiness semantics; re-review was clean. |
| 8 — end-to-end proof | `2fa3ed8`, `c78e260` | One Major test-quality finding showed preview checks could miss newly created files. Complete tree snapshots and a mutation proof corrected it; re-review was clean. |
| 9 — public example and guidance | `d8e1c54`, `fd6f485`, `682d603`, `d2da010`, `6ff2687`, `6c490f4` | Review rounds corrected provider linkage, real-wheel validation, CLI/MCP boundaries, migration and ref guidance, ignored-local ownership, and executable privacy/handbook safeguards. The final re-review was clean. |

Across these reviews, the load-bearing corrections covered atomic metadata
publication, active-lock preservation, exact advertised Git refs, source parsing and
redaction, explicit environment isolation, enrolled/explicit scope compatibility,
complete preview no-write detection, and public artifact privacy. Each correctness,
security, compatibility, or test-quality finding recorded as open by a task reviewer
was resolved or explicitly carried into and resolved by the next task before that task
was accepted.

## Residual review notes

- Task 3 recorded two deferred Minor coverage suggestions: direct cache-integrity
  cases for missing, extra, or symlinked cache entries, and more direct portability
  classification cases. The implementation rejects non-exact cache trees, later
  integration tests cover corruption isolation, and subsequent source-grammar tests
  exercise HTTPS, SSH, SCP, file, and local classifications; the original granular
  cache-entry suggestions were not separately promoted to release blockers.
- External package managers can leave partial side effects when reconciliation fails;
  AI-DLC reports that boundary while preserving its own active lock and cache metadata.
- The Task 10 real-wheel audit found a legacy user-named profile still packaged by a
  directory-wide asset rule. A real-wheel regression failed first, the package rule was
  narrowed to the three approved public profile assets, and the rebuilt wheel passed.
- Linear publication remains local-only because the existing sandbox configuration
  lacks native workflow status IDs. No alternate workspace was queried and no IDs were
  guessed.

## Complete-branch independent review findings and fix round

- Review range: `b256acd..5c3e885`
- Secret containment — Important: normalized tokenization now rejects common
  secret-shaped provider fields such as `api_token`, `client_secret`, camel-case,
  hyphenated, and key variants before cache activation. Exact credential declarations
  and explicitly named environment references remain valid; literal values disguised
  as environment references fail validation, while benign lookalikes remain accepted.
- Git transport trust — Important: canonical cleartext `http://` sources now fail the
  shared source classifier before any Git invocation. HTTPS, SSH, SCP, file URLs, and
  local paths retain their prior classifications.
- Scope composition — Important: `profile show` now always delegates to enrolled-aware
  runtime resolution. An explicit personal or machine file replaces only its matching
  layer, retains the opposite enrolled layer, and composes with an explicit project
  file while preserving value provenance.
- Distribution privacy — Important: the sdist now excludes the legacy user-named
  profile as the wheel already does. The real-artifact regression builds and inspects
  both distributions, requires exactly the three approved public profile assets, and
  rejects enrollment state, local state, environment files, Git metadata, and
  user-specific content.
- Archived documentation — Minor: archived design links now resolve from their moved
  directory, and the canonical capability has the approved purpose instead of the
  archive-generated placeholder.
- Re-review outcome — compatibility: re-review confirmed the four original behavioral
  findings were fixed, then found that plural normalization classified benign schema-4
  integer provider settings `max_tokens = 1024` and `token_count = 10` as credential
  values.
- Adjudicated correction: the grammar now exempts only those two normalized token-metric
  shapes when their values are integers. Exact `token`, singular and plural API token
  fields, access-token fields, client-secret fields, normalized camel-case and
  hyphenated variants, and string values under the token-metric names remain prohibited
  before cache activation. Explicit environment-reference fields remain valid.
- Verification: each behavioral finding, including the compatibility regression, was
  reproduced with a focused failing test before its implementation change and then
  passed its focused regression. Final formatting, typing, generated-file, artifact,
  and required-gate evidence is recorded in the release verification document.
- Decision: the original findings are resolved and the bounded compatibility correction
  is implemented and locally verified. This record does not claim independent approval
  of that correction.

The single allowed final fix/re-review loop is complete. Its remaining concrete
compatibility regression was treated as load-bearing and corrected under the
documented bounded adjudication, so no known review finding remains open; this does
not claim independent approval of the correction. Integration still depends on fresh
controller verification and the required pull request and merged-revision CI.
