# Product-shaping workflow verification

Scope: GitHub issue #11, PS-01 through PS-03. These are local guidance and
packaging results, not live customer, payroll, Claude Code, Antigravity, provider
or platform qualification. No remote publication or completion is claimed here.

## Decision cases

[Inputs and expected rubric](product-shaping/cases.md) were fixed before editing
the three skill bodies. Root ran a fresh, read-only Codex CLI session with
`gpt-5.6-sol`, high reasoning, supplying only the original discovery, prd-draft and
review-inbox bodies and four synthetic inputs. The session was instructed not to
use tools, read plans/specifications or publish work. The evaluator rubric was
withheld. [Baseline output](product-shaping/baseline.md) is retained verbatim.

| Case | Expected decision | Baseline observation |
| --- | --- | --- |
| G: dashboard pressure | Investigate task evidence, compare feasible alternatives, preserve uncertainty | Correctly refused immediate dashboard build and proposed a walkthrough. Did not compare alternatives or assign canonical OUT/RQ IDs. |
| B: contradictory CSV defaults | Investigate contradiction; preserve existing consumer/default contract; proposal is not approval | Correctly identified the contradiction, no opt-in approval and missing live evidence. Proposed a potentially breaking alternative only with a new decision, but did not supply canonical IDs or a complete comparative brief. |
| P: approved non-UI increment | Proceed to needs-spec/configured formal provider; stable IDs; no invented acceptance facts | Recognized bounded opt-in scope and default compatibility, but called unspecified localized column names approved, omitted IDs, and handed off directly to tests/implementation without a specification decision. |
| S: explicitly declined duplicate | Stop with source/reason; no invented reference/publication | Correctly declined republication and did not invent an identifier. |

The baseline already demonstrated useful refusal judgment. The skill edits target
its missing traceability, option comparison and formal handoff, plus the observed
promotion of unspecified format details into approved acceptance criteria. A
positive output contract was chosen instead of adding a new workflow service.

## Paired supplied-assets replay

Root also ran two fresh, equivalent read-only sessions using the same model and
reasoning setting. Both supplied each version's skills and explicitly referenced
assets inline: the original PRD template for baseline, and the updated PRD,
product brief and worked examples for post-change. No tools, rubric, plans or
specification were available to those sessions. This controls for template
availability; it is a small synthetic application check, not a statistically
powered comparison or human quality calibration. G/B deliberately overlap the
worked examples, so this does not establish generalization to unseen products.

[Baseline with assets](product-shaping/baseline-with-assets.md) retained the correct
G/B/S refusal judgments. Unlike the initial skills-only run, it avoided assuming
renamed columns in P; template availability already helped that case. It still
omitted stable IDs and comparative briefs, and its P next action moved from
confirming details to implementation without an explicit needs-spec handoff.

[First post-change output](product-shaping/first-post-change.md) produced the
expected investigate/investigate/proceed/stop decisions. It compared alternatives,
kept approval and missing details distinct, retained default compatibility and
live-evidence limits, mapped RQ IDs to outcomes, and sent P to needs-spec and the
configured formal provider without a required PRD/UI exercise. S preserved the
explicit decline without inventing a tracker ID or publishing work.

The first post-change run was **not a complete pass**: G/B did not explicitly
name their canonical brief owner, and B omitted recovery planning. Following the
skill-authoring guidance for omitted output elements, the final skill adds
required Canonical brief/Owner/Status metadata and explicit Compatibility and
Migration/recovery fields. The [targeted fresh G/B rerun](product-shaping/final-targeted.md) used the final
skill wording and prior supplied assets; the matching explicit fields were then
aligned in the templates/examples as well. Both outputs now name unique chat
briefs, decision owners and draft/source status, retain source-scoped OUT/RQ IDs,
and include Compatibility and Migration/recovery. G remains a bounded learning
slice. B retains the default contract, conditional rollback proposal, unresolved
contradiction and lack of live qualification without approving opt-in behavior.
The targeted omissions are resolved in this synthetic regression. P/S were not
rerun after this structural-only correction; their prior outcomes are preserved
above. Wider harness behavior and user value remain unmeasured.

The displayed Markdown snapshots normalize trailing hard-break spaces. Exact
original response strings are retained for the two affected outputs in
[baseline raw JSON](product-shaping/baseline-with-assets.raw.json) and
[final targeted raw JSON](product-shaping/final-targeted.raw.json); the other
snapshots are unchanged.

## Automated delivery checks

- Before edits, the existing template/rendering suite passed: 331 tests.
- RED: three new init/adopt cases failed because the product-brief asset was
  absent and adoption did not recognize the new managed path as a conflict.
- GREEN: those three passed after adding the brief/examples to the scaffold.
- RED: four selected-harness/provider cases failed because the old discovery
  skill did not point to the brief/examples.
- GREEN: all seven new init/adopt/harness cases passed after skill delivery and
  digest regeneration. Both existing trackers and both supported client adapters
  retain their selected provider guidance; no tracker-specific shaping branch
  was introduced.
- The existing release archive test now checks packaged brief, PRD and examples
  against the source bytes and their scaffold copies. An authored brief conflicts
  without overwriting files or partially adopting the project.

These tests establish delivery, integrity and compatibility. They do not measure
agent judgment through heading assertions. The fresh-session cases above and the
post-change outputs assess actual recommendations and claims.

One intermediate full run had 1,144 passes and one archive-byte comparison
failure: the brief's explicit compatibility fields were edited after the archive
snapshot was built. The differing byte began the old "For an existing product"
paragraph versus the new field list. This was an invalid verification run over
changing inputs, not a product fix. Assets were then frozen for the final required
run; the failure is retained here rather than presented as a passing result.

Final local verification: `ai-dlc project check --required` passed generated,
format, lint, types and test, with **1,145 tests passed** on the frozen assets.
[Local receipt](product-shaping/local-checks.json) correctly records the base
revision and dirty candidate; it is not clean merged-revision completion evidence.
Strict `openspec validate product-shaping-workflow --strict --no-interactive` and
`git diff --check` also passed. The work record validates with its verification link.

## Scope and completion boundary

The September 5 implementation plan remains applicable to this asset slice; its
historical sequencing is not a dependency on another issue. Existing application
services, schema-4 settings, credentials, tracker/SCM behavior and historical Rust
remain unchanged. Supported-client asset rendering is not live harness
qualification and does not establish an Antigravity adapter.

Independent source review, configured merged-revision PR/CI evidence, archival
and `ai-dlc work finish product-shaping-workflow` remain the integration owner's
completion steps. This change does not bypass them or close the remote issue.
