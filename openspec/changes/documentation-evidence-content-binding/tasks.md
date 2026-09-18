# Content-bound documentation evidence

Goal: Deliver #146 without weakening stale-content detection.
Architecture: `documentation/document_impact.py` owns binding, recording and the
gate; CLI and MCP stay thin. Spec: [delta](specs/documentation-impact-workflow/spec.md)
and [design](design.md).

- [ ] 0. Maintainer reviews the reversal of the `merge-freshness` base-mismatch
  rule before implementation starts.
- [ ] 1. Add failing tests in `tests/test_document_impact.py`: two branches with
  disjoint changes and valid evidence merge in either order and both gates pass
  with no rewrite; a bound source changed by the other branch reports stale and
  names it; a changed catalog entry stales only that document; a branch behind its
  target is judged on its own changes; the push-run comparison passes for a merge
  and fails when conflict resolution alters bound content; missing and stale are
  reported separately.
- [ ] 2. Implement schema 2 binding and the merge-base changed set; keep schema 1
  fallback with tests for both directions.
- [ ] 3. Implement merging recording, `--evidence-id`, its default from the bound
  work record, and the kept/added/replaced/dropped report. Add `--prune`.
- [ ] 4. Mirror the gate and recording through MCP; keep deprecated
  `project docs-*` aliases working.
- [ ] 5. Update `docs/development-workflow.md`, `docs/workflows/*` and their
  `project-templates/` copies, documentation skills and `ai-dlc.toml` shared
  guidance that say to refresh base-bound evidence before merge; re-render agents.
- [ ] 5a. Give `project-templates/project/.github/workflows/verify.yml` full-depth
  checkout and `AI_DLC_DOCS_BASE`, matching this repository's workflow, with a
  template test.
- [ ] 6. Migrate this repository: record schema 2 evidence, delete `current.json`.
  Re-measure documentation-evidence commands and commits for this delivery and
  add them to `docs/verification/delivery-path-baseline.md`.
- [ ] 7. Run required checks, validate and archive.
