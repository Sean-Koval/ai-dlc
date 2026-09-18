## Context

Schema 1 evidence is `{base, snapshot, sources, decisions}`. `snapshot` digests the
base commit, the changed set and every source digest together, and the gate first
requires `evidence.base == comparison`. CI supplies the comparison: the pull
request base commit, or for a push the commit the push replaced. A changed set is
computed with a two-dot diff, which is only meaningful when `HEAD` contains the
comparison; hence the refusal to record against an uncontained base.

So evidence goes stale for two unrelated reasons: reviewed content changed
(wanted), or the target branch moved (unwanted when the movement is disjoint).
Storing it at one shared path adds a guaranteed Git conflict on top.

## Goals / Non-Goals

Goals: disjoint branches merge in either order with no evidence rewrite; content
that was reviewed and then changes still fails; the gate's comparison stays
independent of what the evidence claims; fewer manual commands per delivery.

Non-goals: changing how CI selects the comparison, judging semantic accuracy,
automatic decisions, merge-queue integration, pruning as a gate.

## Decisions

**Per-decision binding.** A schema 2 decision is
`{target, outcome, reason, reviewer, bound}` where `bound` maps paths to content
digests. For a catalogued document, `bound` holds the document, every tracked
file matching its `code_paths`, `requirements` and `verification_paths`, and the
digest of that document's catalog entry. For an unmapped changed file, `bound`
holds that file; a deleted file binds a fixed absent marker. The whole
`docs/catalog.toml` is not bound, because unrelated enrollments would stale every
open branch; a changed mapping changes the entry digest or the matched file set.

**Gate.** Resolve the comparison as today (`--base`, `AI_DLC_DOCS_BASE`). Compute
`start = merge-base(comparison, HEAD)` and the changed set as the diff from
`start` to the working tree plus untracked files, with the existing evidence and
work-record exclusions. Derive impacted documents and unmapped files as today. A
required target is satisfied when some decision for it, in any file under
`.ai-dlc/documentation/evidence/`, has a `bound` map equal to the map computed
now. Otherwise it is reported as *missing* (no decision) or *stale* (decision
exists, naming the paths whose content differs). With no resolvable comparison
and no schema 2 evidence, fall back to schema 1 rules.

Using the merge base means a branch that is behind its target is judged on its
own changes, and the push run on the target branch is judged on what the merge
introduced, including any conflict resolution. If another branch changed content
that a decision bound, the digests differ after the update and the decision is
stale — the case `merge-freshness` cared about still fails, and now names the
files. If the other branch was disjoint, nothing is stale.

**Any file may satisfy a target.** The gate does not need to know which work item
owns a change. Old evidence files are inert: their digests stop matching when
content moves on. `docs review --prune` lists and, with `--apply`, removes files
with no matching decision; it never gates.

**Recording.** `ai-dlc docs review --disposition <file> --reviewer <name>
[--evidence-id <id>]` writes `.ai-dlc/documentation/evidence/<id>.json` itself.
`<id>` defaults to the work record bound to the current branch and is otherwise
required. Existing decisions in that file whose `bound` map still matches are
kept; supplied decisions replace or add targets; decisions for targets no longer
required are dropped. Supplying a decision for an unrequired target is still an
error. Output reports kept, added, replaced and dropped targets. Stdout-only
recording remains when `--evidence-id -` is given.

**Rejected.**
- *Keep one file, add a merge driver or `--refresh`.* Still one commit and one CI
  cycle per target movement, and merge drivers need per-clone configuration.
- *Compute everything at the gate, commit nothing.* Decisions are human or agent
  judgments with reasons; they must be stored somewhere reviewable. Pull request
  bodies are not available to the push run or to `work finish` offline.
- *Per-work files but keep exact-base binding.* Removes the Git conflict and
  keeps the re-record after every target movement, which is most of the cost.
- *Trust the evidence's recorded base.* Rejected before and still rejected; the
  comparison stays independent.

## Risks / Trade-offs

- A disjoint change on the target can still alter what a document *should* say
  without touching anything bound to it. Schema 1 forced a re-record there, but
  the re-record was mechanical and reviewed nothing, so little is lost. The
  existing limitation statement remains.
- Evidence files accumulate like work records. Pruning is manual.
- A reviewer name per decision makes mixed authorship visible but lengthens files.
- The merge-base computation needs history. This repository's workflow checks out
  with full depth and sets `AI_DLC_DOCS_BASE`; the project template's
  `verify.yml` does neither, so generated projects currently gate against the
  evidence's own recorded base. The template gains both settings in this change.
  A shallow checkout fails with the existing "Git comparison unavailable" error
  rather than passing.

## Migration Plan

Ship schema 2 reading and writing with the schema 1 fallback. In this repository,
record the delivery's own evidence as schema 2 and delete `current.json` in the
same change. Generated projects keep passing on `current.json` until their next
recording, which writes schema 2; guidance tells them to delete `current.json`
then. Remove the fallback in the following release, matching the alias policy in
DI-01.
