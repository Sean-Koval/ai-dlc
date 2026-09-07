# Requirements-to-delivery traceability verification

Scope: GitHub issue #12, TR-01–TR-03, on the committed #11 product-shaping
interface. Evidence here is local code/packaging verification and limited synthetic
consumer exercises. It does not establish live tracker, payroll, client or platform
qualification, human preference, or merged-revision completion.

## Design and compatibility

The current issue/spec and September 7 work-computer roadmap take precedence over
historical Linear sequencing. Root confirmed the bounded implementation rules:
validate the selected reachable graph, preserve empty defaults and pinned binding
identity, treat only canonical closed as completed, and reconcile existing issues
before richer first-creation bodies. No vendor branch was added to WorkService.

The existing journal gained a read-only lookup so richer publication can recover
old results without changing original payload fingerprints or operation IDs. No
new journal schema, provider operation or service-specific workflow was added.
CLI validation shares the same graph/document reader as publication/start and
never instantiates a mutation journal or calls remote providers. Existing MCP
publish/start entry points consume the same guarded WorkService implementation.

## Test-first regressions

- Pure graph/body boundary: 11 new tests initially failed because the functions
  were absent, then passed. Graph cases cover missing IDs, unsafe IDs, mismatches,
  self/cycles, deterministic errors, shared dependencies and a 1,500-node chain.
- Optional Work fields first failed on missing defaults/unsupported fields. After
  adding defaults, publication/refusal tests exposed the actual missing guards:
  13 failures for graph/artifact checks, richer body and dependency start behavior.
  The integration then passed those cases and the older workflow/CLI suite.
- Blank/whitespace/multiline requirement identifiers initially passed model
  validation; three tests failed, then passed after single-token validation.
- Legacy-journal recovery covers mapped/correlated issues, delayed correlation
  indexes, succeeded prior results and uncertain/pending creates. Authored issue
  bodies, original fingerprints and correlation/operation identity are preserved.
- Dependency tests use isolated tracker fixtures and real temporary Git branches.
  They prove refusal before branch/binding/tracker effects for incomplete,
  cancelled, duplicate, unknown and unavailable states; transitive reads are fresh
  and use the dependency's pinned provider. They are not live service evidence.
- CLI validation initially failed as an absent command, then passed with exit
  codes 0/1, PATH empty, unchanged project files, no state-directory creation and
  an unrelated malformed draft excluded from the selected closure.
- The delivery-asset test initially failed on the absent template, then passed
  when templates/examples and client copies shipped together. Adoption creates no
  work items. Release packaging checks compare both wheel and source-distribution
  assets against their source and scaffold copies.

## Consumer pressure cases

[Inputs](spec-delivery-traceability/cases.md) were fixed before skill edits. Root
ran a fresh read-only Codex CLI session using gpt-5.6-sol/high, supplying only the
original spec-from-prd skill and those synthetic cases. No tools, implementation,
plans, rubric or formal specification were available. The
[baseline](spec-delivery-traceability/baseline.md) preserves the response; its
[raw JSON](spec-delivery-traceability/baseline.raw.json) retains exact whitespace.

The baseline already resisted ticket-per-checkbox and shared-epic-spec pressure,
kept unavailable sandbox evidence honest, and blocked cancelled prerequisites.
Those judgments are not claimed as newly discovered benefits. It did not supply
concrete draft Work fields/IDs, a machine-readable no-spec decision, or distinguish
local graph validation from fresh dependency completion checks. Its traceability
also lacked the full source/scenario/work/implementation/evidence mapping.

The new skill supplies an explicit delivery artifact contract, retained RQ
ownership, separate behavior and verification examples, and the actual
validation/start rules. Examples are synthetic document destinations, not
published work or invented live observations. Post-change exercise results are
recorded separately from automated tests; they do not establish general quality
calibration or consume the repository's human-rated experiment budgets.

The [post-change consumer output](spec-delivery-traceability/post.md), with
[exact raw response](spec-delivery-traceability/post.raw.json), used the same
synthetic inputs in a fresh equivalent session with the new skill and its
referenced assets supplied. A1/A2 each own an independently finishable change,
proposed local Work IDs, mapped RQ references, dependencies and tasks. Unknown
formats/error semantics stay unresolved rather than copying the worked example's
synthetic choices. B explicitly uses requires_spec=false/spec_reason, keeps its
existing archive/dependency and refuses live completion without access. C retains
cancelled as a blocking state, prepares only a local draft and distinguishes a
valid graph from completion. No validation, file existence, approval or remote
publication is invented. These observed cases satisfy the scoped consumer rubric;
they do not establish unseen-case generalization or human-rated calibration.

A further ordering regression exposed a stale service configuration creating a
branch before its save-time guard rejected the changed project. The test failed
on `work/target` instead of `main`; the same source guard now runs before graph,
dependency or branch effects. The workflow/CLI/pure/MCP suite then passed 118 tests.

## Required local checks

All five required manifest checks passed: generated assets, formatting, lint,
types and the full test suite. The suite contains 1,183 collected tests; the
required test command exited 0. The [receipt](spec-delivery-traceability/local-checks.json)
records the dirty candidate based on `0b8abb8`, before its final guidance/evidence
commit; it is not an exact merged-revision receipt. Strict OpenSpec validation
also passed. Offline validation of the actual `spec-delivery-traceability` record
returned valid with the `product-shaping-workflow` dependency and no errors.
Source, assets and tests stayed unchanged throughout the required checks.

## Completion boundary

Required checks, strict OpenSpec validation, source review and configured exact
merged-revision evidence remain authoritative. Archive, PR/CI integration and
`ai-dlc work finish spec-delivery-traceability` belong to root integration. This
work does not weaken gates, mutate the tracker, or claim a completed work computer
or harness walkthrough.
