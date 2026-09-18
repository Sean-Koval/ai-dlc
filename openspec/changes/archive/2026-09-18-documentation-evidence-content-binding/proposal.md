# Bind documentation evidence to content, per work item

## Why

Issue #146. Every delivery branch rewrites one committed file,
`.ai-dlc/documentation/current.json`, and that evidence is valid only for one
exact comparison commit. Two consequences follow:

- Any two open pull requests conflict in Git as soon as one merges, even when
  their changes are disjoint (#142 and #143 on September 18, 2026).
- Whenever the target branch moves, evidence must be recorded again although no
  decision changed. The [delivery path baseline](../../../docs/verification/delivery-path-baseline.md)
  counts 90 of 450 non-merge commits rewriting this file.

The archived `documentation-evidence-merge-freshness` change chose exact-base
binding deliberately and named this cost: "Frequent target movement requires
repeated re-recording." It also rejected merge queues because "exact-base evidence
cannot anticipate queued predecessors." This change revisits that decision. It
keeps what that change protected — the gate's comparison is resolved
independently of the evidence, and evidence for changed content never passes —
and removes the dependence on an exact base commit.

## What Changes

- Evidence is stored per work item under `.ai-dlc/documentation/evidence/<id>.json`
  (schema 2), so branches do not share a path.
- Each decision binds the content digests of its own target and that target's
  mapped sources, instead of the whole evidence binding one base commit and one
  changed set.
- The gate computes the changed set from the merge base of the supplied
  comparison and `HEAD`, then requires every impacted document and unmapped
  changed file to have a decision, in any evidence file, whose bound digests equal
  current content.
- Recording merges into the work item's evidence file: still-valid decisions are
  kept, and only new or stale targets need a decision.
- **BREAKING (gate behavior):** a moved target branch alone no longer fails the
  gate. The base-mismatch error and the refusal to record against a base outside
  `HEAD` are removed. Schema 1 `current.json` keeps passing under its existing
  rules for one release when no schema 2 evidence exists.

## Capabilities

### Modified Capabilities
- `documentation-impact-workflow`: DI-02 changes from revision-bound to
  content-bound dispositions.

## Impact

`src/ai_dlc/documentation/document_impact.py`, the `docs review` and `docs gate`
CLI and MCP entry points, their tests, the development workflow, project
template guidance and documentation skills that tell users to refresh base-bound
evidence before merge, and generated `AGENTS.md`. CI base selection
(`AI_DLC_DOCS_BASE`) is unchanged. No remote setting is changed.
