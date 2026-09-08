## A — Draft brief/rubric and blocked generation handoff

**Brief: library-room branch selection**

- Owner/status: Maintainer; **draft—material decisions unresolved**
- Source: `docs/product/rooms.md`; delivery slice `rooms-choice`
- References: `OUT-ROOM`, `RQ-LOCATION`
- Outcome: Help patrons confidently select the intended branch before reserving its room.
- Audience/journey: Patron chooses a branch, reviews rooms, and reserves at that same branch.
- Supplied evidence: Request for a “reassuring and distinctive” selection experience; one day already spent polishing.
- Hypotheses: Clear selected-state treatment and contextual confirmation may increase confidence.
- Scope: Branch-selection presentation and confirmation cues.
- Non-goals: New navigation, replacement component system, unrelated reservation-flow changes.
- Constraints: Preserve existing components and navigation; distinctiveness must remain consistent with the existing brand.
- Unresolved: Meaning of “distinctive”; accessibility target; required rating threshold; task budget; iteration/time ceiling; approval source/status.

**Proposed rubric `room-r1-draft`**

- `FLOW-LOCATION` → `RQ-LOCATION`, required behavior: given branch choices, when a patron selects a branch and proceeds, the selected branch is the one reserved. Evidence requires an interaction trace including confirmation and reload/persistence if persistence is expected.
- `SELECTION-CLARITY` → `RQ-LOCATION`, proposed 0–4 rating:
  - 1: Selected branch is difficult to distinguish or confirmation is ambiguous.
  - 3: Selected branch is immediately identifiable and consistently named at the booking decision.
  - 4: Level 3 plus reassuring contextual cues that are distinctive while fitting existing brand/components.
- Required states: default, selected, focus, error/recovery, confirmation.
- Proposed viewports/fixtures: 390px and desktop; at least two similarly named branches.
- Evidence: Supplied captures may support visual ratings; browser traces are required for interaction behavior.
- Proposed threshold: minimum 3. **Not approved.**
- Accessibility target: **unresolved**, so focus/contrast requirements cannot be finalized.

**Run decision:** No generator, candidate, approved budget, iteration ceiling, time/token ceiling, or stop condition is settled. Prior polishing does not authorize more generation. Next session must obtain owner approval for the accessibility target, rubric threshold, budget and ceilings—then version the rubric and hand the approved contract to the selected generator.

---

## B — Evaluation and selection

**Evaluation: c1 revision 111; rubric `room-r1`**

- Review mode: Supplied independent synthetic evidence only; no new execution.
- `FLOW-LOCATION`: **Fail.** Expected North Annex to remain selected after confirmation/reload; observed East Hall.
- `KEYBOARD`: **Unverified.** No keyboard observation exists.
- `CLARITY`: **4**, based on the supplied independent synthetic rating and its stated rubric alignment.
- Generator’s 5/5 self-rating and predicted ease of repair are not evaluation evidence.

**Finding:** Required location persistence is defective and can cause reservation at the wrong branch. Correct persistence/state restoration, then reproduce selection → confirmation → reload and verify North Annex remains selected. Separately execute the complete reservation by keyboard.

**Verdict:** **Needs work; not accepted.** A high clarity rating cannot compensate for a required failure or missing required evidence.

**Selection decision:** Do not select c1 for release or present it as passing. It may be shown only as a clearly labeled non-release visual prototype, with the known persistence failure and unverified keyboard behavior disclosed. The ten-minute deadline and afternoon cost do not change the verdict. Next session should retest a fixed, identified revision against both required behaviors and retain this report.

---

## C — Static-only evaluation and handoff

**Evaluation: c2 revision 222**

- Review mode: **Self-review of a supplied screenshot**, not independent review.
- Evidence: One textual screenshot description at 390px; booking action visible. No running candidate, browser, second evaluator, or human review.
- Visual action hierarchy: **Unverified.** Visibility alone does not establish the rubric’s hierarchy anchors; the actual image is absent.
- Keyboard focus restoration: **Unverified.** Static evidence cannot establish focus behavior.
- Persisted branch choice: **Unverified.** Static evidence cannot establish state across reload.
- Generator claim that interactions work: Not evidence.

**Verdict:** **Unverified; not releasable as “everything passed.”** No known failure is established, but all required criteria lack sufficient evidence.

**Handoff:** A fresh independent session or human reviewer needs access to the exact c2 revision and rubric. At required viewports, inspect visual hierarchy against anchors; operate the flow by keyboard and verify focus restoration; select a branch, confirm, reload, and verify persistence. Record traces/captures with immutable candidate identity. Do not describe this review as independent.

---

## D — Selection across rubric versions

**Decision under `room-r1`:** Select **c1 revision 111**. It passes every required check and meets required ratings at 3. Retain c2 despite its stronger ratings, but it cannot win because `FLOW-LOCATION` fails. c3 remains unverified because it is static-only. Recency and cost are not quality criteria.

**Under proposed `room-r2`:** Nothing can be selected or claimed compliant. Adding required confirmation detail is a material rubric change; finalize/version `room-r2`, then reevaluate every candidate being compared. Existing `room-r1` reports remain valid only for `room-r1`.

**Budget:** No more revisions are authorized: initial candidate plus two revisions and the 30-minute ceiling are exhausted. Reevaluation may proceed only if covered by existing review authority; generation of another revision requires explicit new budget approval.

**Next action:** Owner decides whether `room-r1` selection is sufficient or formally approves `room-r2` and a bounded reevaluation plan. If no existing candidate satisfies r2, retain needs-work/unverified and request a separately authorized revision budget.