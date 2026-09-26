## 1. Specify and review

- [ ] 1.1 Validate this change with `openspec validate capability-scoped-guidance --strict`; link NH-06/TR-04 and this task artifact from the parent-owned work record.
- [ ] 1.2 Review `src/ai_dlc/harness/agents.py`, `src/ai_dlc/providers/__init__.py`, `modules/components.json` and `src/ai_dlc/work/workflow.py` against the design matrix; keep runtime-kind and component identity distinct.

## 2. Implement the bounded renderer change

- [ ] 2.1 Add parameterized matrix coverage in `tests/test_agents_phases.py` for omitted roles, partial/full built-in selections, all four tracker kinds, `kind`/`type` aliases and precedence, custom components, misleading `component=openspec`, empty finish gates, and required documentation gate present/absent.
- [ ] 2.2 Keep worker edits limited to source/tests; the parent owns shared docs and generated assets. Make `_shared_guidance_lines` and its caller in `src/ai_dlc/harness/agents.py` use project-selected runtime capabilities without adapter execution, network calls, new schema or changed lifecycle gates. Preserve every required check and missing-command marker.
- [ ] 2.3 Extend `tests/test_rendering.py` for full-to-local render, local-only adoption, client consistency, unchanged authored prefix/suffix, edited-managed-body refusal and idempotence; preserve provider/bundle/team ownership tests and custom provider links.

## 3. Document and verify

- [ ] 3.1 Update `docs/runbooks/machine-enrollment.md`; review `docs/workflows/design-to-implementation.md`, `docs/verification/documentation-workflow.md` and actual catalog-mapped impact. Record content-bound documentation dispositions with the existing documentation workflow, without inventing qualification evidence.
- [ ] 3.2 In this checkout's prepared source environment run `uv run --locked --no-sync pytest -q tests/test_agents_phases.py tests/test_rendering.py tests/test_company_guidance.py tests/test_workflow.py` to verify instruction selection, managed ownership and unchanged lifecycle behavior.
- [ ] 3.3 Parent-owned: regenerate this repository's owned AGENTS/CLAUDE/native guidance assets with `ai-dlc agents render --apply`, inspect the diff for preserved authored text, then run `ai-dlc agents render --check` and `uv run --locked --no-sync python scripts/check_generated.py`.
- [ ] 3.4 Run `openspec validate capability-scoped-guidance --strict`, `ai-dlc work validate --all` and `ai-dlc project check --required` using the checkout's prepared environment. Record actual results, fix failures and update affected documentation dispositions only when stale.

## 4. Deliver through the existing lifecycle

- [ ] 4.1 Have the parent-owned reviewed work record reference this independently finishable change and its validation evidence; keep tracker acceptance concise and linked to the authoritative tasks here.
- [ ] 4.2 Archive with `ai-dlc work archive capability-scoped-guidance` on the delivery branch before merge, update from the target branch and rerun required checks, then use `ai-dlc work finish capability-scoped-guidance` at the merge revision after normal review/merge and evidence gates pass. Do not infer remote authorization from these task instructions.
