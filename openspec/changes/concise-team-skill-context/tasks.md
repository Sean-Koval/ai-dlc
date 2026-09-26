## 1. Specify and preserve the current boundary

- [ ] 1.1 Validate `concise-team-skill-context` with OpenSpec and bind the parent-managed work record to TS-02, TS-05, TS-06 and TS-07; retain existing TS-01/03/04 and NH-01/03 guarantees.
- [ ] 1.2 Add focused observable regression cases in `tests/test_team_sources.py` for indexed selection, exact skill bytes, full rules, native and teamai layouts, bounded descriptions and fallback/escaping.

## 2. Render concise discovery

- [ ] 2.1 Update `src/ai_dlc/harness/team_source_render.py` to retain full skill exports and rules while building deterministic bounded discovery entries; reuse safe YAML parsing without relaxing teamai validation or imposing new native frontmatter requirements.
- [ ] 2.2 Pass effective clients and the existing destination mapping from `src/ai_dlc/harness/agents.py`; deduplicate shared destinations, support explicit client rendering and preserve inline access with no selected clients.
- [ ] 2.3 Verify actual link resolution in `tests/test_native_harnesses.py` for Claude-only, Codex-only, Antigravity-only and mixed renders, including Antigravity rule rebasing, shared ownership and native activation metadata.

## 3. Preserve updates, conflicts and evidence

- [ ] 3.1 Cover intact legacy-section migration, dry-run no-write behavior, repeated clean render, authored/edited conflicts and unchanged ownership schema/provenance in `tests/test_team_sources.py`.
- [ ] 3.2 Extend or reuse selection removal/reselection, explicit sync update and transactional failure/recovery coverage; verify entries and active skill files stay consistent while retained backups and unselected-client files remain protected.
- [ ] 3.3 Add a deterministic short/long-body fixture and record old/new UTF-8 guidance and complete skill-file byte counts; assert body growth leaves concise guidance unchanged without converting bytes into claimed token savings.

## 4. Document and verify delivery

- [ ] 4.1 Update `docs/runbooks/machine-enrollment.md` to explain concise discovery, unchanged full rules/files, manual native-discovery fallback and the empty-client exception.
- [ ] 4.2 Review `docs/architecture.md`, `docs/release-verification.md` and `docs/catalog.toml`; update affected mappings and record content-bound documentation-impact dispositions in the work workflow.
- [ ] 4.3 Run focused team-source/native-harness tests, `openspec validate concise-team-skill-context --strict` and required project checks in the prepared checkout; record actual results without claiming live client qualification.
- [ ] 4.4 Complete parent-owned review, OpenSpec archive, target-branch freshness checks and `ai-dlc work finish` through the normal delivery workflow.
