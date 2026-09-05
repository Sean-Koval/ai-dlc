# Design PM: portable briefs, evaluation, and iteration

Owner: AI-DLC project maintainer
Status: planned optional UI/UX workflow within milestone M2; implementation and live evaluation pending
Updated: 2026-09-05

This proposal consumes the broader [product-shaping workflow](../../openspec/changes/product-shaping-workflow/proposal.md)
and [delivery traceability](../../openspec/changes/spec-delivery-traceability/proposal.md).
The [framework direction](../product-direction.md) owns the product strategy;
this document owns UI/UX-specific rationale and example evaluation criteria.
Execution details are in the [implementation plan](../superpowers/plans/2026-09-05-design-pm-workflow.md).

## Problem and audience

AI-DLC equips development harnesses with reproducible tools, repository structure,
Markdown guidance, and consistent workflows across machines. The harness runs the
development process. CLI services support setup, validation, traceability, and
evidence gates where applicable; every development action need not pass through
the CLI. Existing project completion policies remain in effect.

The intended audience is a developer using a harness such as Codex, Claude Code,
Antigravity, or Pi to turn a product idea into a usable interface. Current client
fixtures cover Codex and Claude Code only; this proposal does not establish support
for the other clients.

Today the repository has discovery, PRD, specification-decision, and handoff
guidance, plus a design template. It does not supply a complete way to turn a
design preference into a repeatable evaluation. A request to make an interface
good leaves the evaluator inventing the target after seeing the result.

## Source and adaptation

Anthropic's [harness-design article](https://www.anthropic.com/engineering/harness-design-long-running-apps)
uses separate generation and evaluation, four design axes (design quality,
originality, craft, functionality), example-based evaluator calibration, and
inspection of running interfaces. Its game-editor example catches rectangle fill
that places only endpoint tiles. Later experiments simplify orchestration as model
capability changes. These are experimental findings, not a universal recipe.

The artifact layout, example rubric, thresholds, budgets, and delivery plan below
are proposed AI-DLC choices. They are not measurements or prescriptions from the
article.

## Outcomes and acceptance

1. A harness can take a short product request and produce a brief that identifies
   audience, primary task, constraints, references, and observable success.
2. Before generation, the work has a versioned rubric with criterion IDs, evidence
   methods, score anchors, required checks, and an explicit evaluation budget.
3. A fresh evaluator can inspect an identified candidate and produce actionable
   findings without receiving the generator's self-rating as its evidence.
4. A later session or another supported harness can continue from the saved brief,
   rubric, candidate, findings, and unresolved decisions.
5. Deterministic failures, subjective ratings, and missing evidence remain distinct.
   A high visual rating cannot compensate for a failed required user journey.
6. A separate calibration exercise measures whether the workflow improves human
   preference and defect detection enough to justify its cost.

## Scope and exclusions

The first delivery is a portable workflow package: skill guidance, templates,
examples, and project-generation integration. The two skills are design-brief
for brief/rubric creation and design-evaluate for independent review. Generation
uses the selected existing visual tool or skill.
Reuse the existing discovery and PRD stages; Design PM supplies their design-specific
verification detail. Existing visual-design tools can perform generation.

No mandatory orchestration daemon, new hosted service, hard-coded model, or fixed
three-agent process is required. One harness can sequence separate sessions or
use its native delegation if available. A human can perform independent review.
When independence is unavailable, record self-review explicitly.

This change does not add UI code to AI-DLC, change its finish gates, install new
client integrations, introduce a credential loader, or require a new CLI command.
Automation is a later option if the manual artifact workflow proves useful.

## Proposed workflow

1. **Brief:** capture users, intended tasks, scope, constraints, style references,
   existing design-system commitments, and unresolved product decisions.
2. **Evaluation contract:** translate the brief into checks and rating anchors;
   identify viewports, states, fixture data, evidence, reviewers, and budget.
3. **Generate:** create an identified candidate against that brief and contract.
4. **Evaluate:** a separate reviewer exercises the candidate, records evidence,
   and ties each finding to a criterion and reproducible state.
5. **Iterate:** address prioritized findings, retest affected behavior, and retain
   the previous candidate so selection can favor an earlier revision.
6. **Select and hand off:** record the chosen candidate, residual findings, and
   human decisions; use `needs-spec` and OpenSpec for implementation behavior.

Design iteration can overlap implementation. The selected artifact and evaluation
contract travel with the work; they do not replace regression tests or repository
completion policy.

## Starter rubric: an onboarding interface example

These examples describe a hypothetical interface for a developer tool, not an
existing AI-DLC UI. Projects adapt them before running an evaluation.

| Axis | Concrete example criterion | Evidence |
| --- | --- | --- |
| Design quality | Connection, review, and success screens use the same named text styles and action hierarchy; the current setup step is identifiable on each. | Screenshots of all three states with marked inconsistencies. |
| Originality | Workspace selection uses relevant identity and permission details; decorative dashboard panels do not displace the user's connection task. Existing brand components are welcome when they fit the brief. | Compare the candidate with the brief and explain specific choices. |
| Craft | At the agreed mobile and desktop widths, long workspace names do not obscure the primary action; visible keyboard focus is not clipped or covered. | Browser inspection with long-name fixtures and keyboard traversal. |
| Functionality | Starting disconnected, a user selects the intended workspace, reviews the selection, and reaches a working connected state. A rejected credential permits correction without silently switching workspaces. | Reproducible interaction trace and observed application state. |

Every subjective criterion uses a proposed 0–4 scale: 0 contradicts the criterion;
1 has major shortcomings; 2 partly meets it; 3 meets it with evidence; 4 exceeds
it in a way that serves the brief. Each criterion needs its own examples of 1,
3, and 4; the generic scale alone is insufficient calibration. Missing observation
is `unverified`, not a zero or a passing score.

Starter selection rule: all required behavioral checks pass, each required rated
criterion reaches 3, and no required evidence is missing. These are unvalidated
starting defaults. A project can choose different thresholds before the run.
Optional weighted scores rank candidates only after required checks pass.
An existing enterprise design system can prioritize consistency; originality does
not require novelty, unusual navigation, or a new component library.

Each check records an ID, applicable state, setup, action, expected observation,
method, severity, and evidence location. For example:

- `FLOW-01`: Given two similarly named workspaces, select the second, review its
  identifier, connect, reload, and verify that the second remains selected.
- `RECOVERY-01`: Reject a credential, correct it, and retry; verify the error clears
  and no duplicate connection or unintended workspace selection appears.
- `KEYBOARD-01`: Perform the primary journey using only keyboard controls; verify
  reachable controls, visible focus, and focus restoration after closing a dialog.
- `NARROW-01`: At the agreed narrow viewport, open validation feedback with a long
  workspace name; verify the message and retry control remain visible and usable.

These are acceptance examples, not a complete accessibility compliance assessment.
Static mockups can support visual review but leave interaction checks unverified.

## Artifacts and ownership

Suggested project paths (created when a design task needs them):

- `docs/design/<work-id>/brief.md`: rationale, audience, scope, references.
- `docs/design/<work-id>/rubric.md`: versioned criteria and example anchors.
- `docs/design/<work-id>/iterations/<candidate-id>/evaluation.md`: revision,
  tools/model, criteria version, observations, scores, findings, and verdict.
- `docs/design/<work-id>/decision.md`: chosen candidate, rationale, remaining gaps.

Evidence links identify the candidate revision, viewport, fixture, and capture.
Use repository-approved storage for recordings and screenshots; exclude secrets
and private user data. The report records an evidence digest or immutable artifact
reference. Formal requirements stay in OpenSpec. Linear stores work status and
priority. These Markdown artifacts are usable directly by the selected harness.

## Iteration and evaluation of the workflow

Proposed starter budget: one initial candidate plus at most two revision rounds,
with a project-selected time or token ceiling recorded before execution. Stop on
meeting the contract, exhausting the budget, a material product decision, or two
consecutive evaluations with no criterion improvement and no required defect
resolved. Plateau can end the run without success. Preserve the best candidate
that meets the contract; record `needs-work` when none does. Human overrides are
recorded and cannot relabel a failed test or supply absent evidence.

Evaluate the evaluator as well as the UI. Build original calibration cases that
include a polished but broken journey, a plain usable interface, a deliberate
brand constraint, an inaccessible interaction, and a screenshot-only mockup.
Have humans label defects and explain taste preferences before tuning prompts.
Reserve held-out cases to detect overfitting.

Compare (a) current guidance, (b) rubric-only generation, and (c) rubric plus
independent evaluation on matched tasks and fixed recorded budgets. Record human
pairwise preference, missed required defects, false-positive findings, rater
disagreement, actual usage when available, and elapsed time. Counterbalance order
and hide condition labels from human raters where practical. Repeat runs; do not
claim general improvement from one favorable example. Keep human review pending
until a human supplies it.

`agents/evaluation.toml` currently describes evaluations of AI-DLC's judgment
skills, not this UI workflow. Preserve its existing protocol and budget; the
Design PM experiment needs its own declared cases and budget.

## Constraints, risks, and open questions

- Score gaming: keep examples and criteria stable during a comparison; a material
  rubric change creates a new version and requires rescoring retained candidates.
- Aesthetic bias: use project-specific references and human calibration; do not
  treat one evaluator's preference as objective beauty.
- Missing tools: preserve portable instructions and report unverified checks when
  a harness cannot inspect the required browser state.
- Portability claims: separately qualify each client; readable Markdown alone
  does not prove hooks, browser tools, or delegation work on that client.
- The execution plan fixes skill names and the Markdown artifact contract. Each
  design task chooses brand references, accessibility target, and run budget
  before evaluation; these are task inputs rather than unresolved framework scope.

## Links

- [Roadmap](../roadmap.md)
- [Current design handoff](../workflows/design-to-implementation.md)
- [Formal proposal](../../openspec/changes/design-pm-workflow/proposal.md)
- [Implementation work record](../../.ai-dlc/work/design-pm-workflow.toml)
- [Calibration work record](../../.ai-dlc/work/design-pm-calibration.toml)
- [SAN-6: workflow backlog ticket](https://linear.app/sandbox-aidlc/issue/SAN-6/add-portable-design-pm-briefs-rubrics-and-evaluation-workflow)
- [SAN-7: calibration backlog ticket](https://linear.app/sandbox-aidlc/issue/SAN-7/calibrate-design-pm-evaluation-and-measure-quality-versus-cost)
