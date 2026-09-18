# Delivery path baseline

Measured September 18, 2026 at `78e9329` from this repository's own Git and pull
request history. It is the starting point for the roadmap's "shorter delivery
path" increment and the template for the adoption friction log. It measures
process cost only; it says nothing about whether the gates caught real defects.

## Method

- Commit counts use `git log --no-merges main`. A commit is *process-only* when
  every path it touches is under `.ai-dlc/` or `docs/verification/`.
- Pull request samples use `gh pr view <n> --json commits,files`.
- Command counts follow the [tool map](../workflows/tool-map.md) and the behavior of
  `src/ai_dlc/work/workflow.py` and `documentation/document_impact.py` at this
  revision, for a change that needs a specification. They count commands a person
  or agent must issue, not commands AI-DLC runs itself. The checklist embedded in
  issues filed before September 14 (for example #85) predates #72–#75 and
  overstates the path: `work new --from-issue` now records the tracker artifact,
  `work pr` links the pull request, and work-record edits no longer invalidate
  documentation evidence.

This repository is the only adopter measured. Its history includes evidence
records for its own qualification, which a downstream project would not write, so
treat the repository-wide share as an upper bound.

## Repository-wide

| Measure | Count | Share of 450 non-merge commits |
| --- | --- | --- |
| Process-only commits | 335 | 74% |
| `chore(work)` commits (record, link, start) | 103 | 23% |
| Commits rewriting `.ai-dlc/documentation/current.json` | 90 | 20% |

## Sampled deliveries

| Pull request | Substantive change | Commits | Process commits | Process files |
| --- | --- | --- | --- | --- |
| #136 README refresh | 1 file, 194 lines | 4 | 2 | 2 of 3 |
| #132 Jira preparation | documentation | 5 | 4 | — |
| #133 FDE scaffold | 302 lines source, 262 lines tests | 9 | 6 | 2 of 19, plus 5 OpenSpec files |

The smallest change pays the highest proportional cost: a one-file README edit
needed a 33-line work record, a documentation snapshot and two record commits.
In #133 the documentation snapshot alone was 139 added lines and was rewritten
after the merge refresh.

## Manual commands, tracker item to finish

| Step | Commands | Repeats |
| --- | --- | --- |
| Draft and review the record | `work new --from-issue`, edit, commit | once |
| Specification | author change, `openspec validate` | once |
| Start | `work start` | once |
| Implement and check | `project check --required` | per iteration |
| Documentation evidence | `docs-impact`, write decisions JSON, `docs-disposition`, commit | **after every non-record branch edit**: implementation, archive, merge refresh |
| Archive | `work archive` | once |
| Pull request | `work pr`, push | once |
| Pre-merge refresh | merge target, re-check | once or more |
| Finish | switch to merge commit, wait for CI, `work finish` | once |

Baseline: about 11 distinct commands on the shortest path, with the four-step
documentation evidence sequence repeated at least three times, for roughly 20
issued commands. The roadmap target is to halve that. These counts are derived
from reading the code, not from an observed run; the adoption friction log
replaces them with observed numbers.

## Candidate reductions

Ordered by commands removed per delivery; each needs its own issue and, where
gate behavior changes, an OpenSpec change.

1. **Record documentation evidence once, at the gate.** Compute dispositions in
   `work pr` and the pre-merge refresh instead of requiring a committed snapshot
   after every edit. #75 exempted record-only edits; implementation, archive and
   the merge refresh still each force a rewrite. Removes about eight commands per
   delivery and most of the 90 snapshot commits.
2. **A light path for changes with no specification decision.** When the record
   says `spec required: no` and the diff is documentation only, let the pull
   request body carry scope and acceptance instead of a committed work record.
   #136 would have been one commit.
3. **Refresh the embedded delivery checklist.** Open issues still carry the
   pre-#72 ten-step checklist, so agents following them issue commands the engine
   no longer needs. Replace it with a link to the current workflow.
4. **One pre-merge command.** `work refresh` that merges the target, recomputes
   evidence and runs required checks, replacing three separate steps.

## After content-bound evidence — September 18, 2026

Candidate reduction 1 was delivered as per-work, content-bound evidence (#146).
Observed on that delivery itself, one item on one repository:

| Measure | Schema 1 path | This delivery |
| --- | --- | --- |
| Evidence recordings | after implementation, after archive, after each target movement | 2: after implementation and after archive |
| Decisions written at the second recording | all 16 again, plus the new targets | only the new and stale targets; the rest were kept |
| Evidence-only commits | one per recording | 1; the first recording rode the implementation commit |
| Git conflict on evidence when another pull request merges first | always | none possible; the path is per work item |

The archive step still forces a second recording because it moves the change's
files and promotes a specification that a mapped document depends on; the gate
named exactly those targets. Halving the roughly 20 issued commands still needs
candidates 2 and 4. The deleted `current.json` removes the per-target-movement
rewrite, which the repository-wide count put at up to 90 of 450 commits; that
saving is projected, not yet observed across concurrent pull requests.

## Friction log

Adopting repositories keep this table in their ignored `.ai-dlc/local/friction.md`
for the two-week run, then file issues from it. One row per event, written when it
happens.

| Date | Work ID | Step | Kind | What happened | Minutes lost | Worked around by |
| --- | --- | --- | --- | --- | --- | --- |
| | | | refusal / repeat / confusion / missing / bug | | | |

Kinds: *refusal* — a gate blocked correct work; *repeat* — the same command
issued again with no new information; *confusion* — the next command was unclear;
*missing* — the workflow had no place for something needed; *bug* — incorrect
behavior. Also record, per delivered item: commands issued, process-only commits,
and whether a gate caught a real problem. That last observation is the evidence
for keeping a gate.
