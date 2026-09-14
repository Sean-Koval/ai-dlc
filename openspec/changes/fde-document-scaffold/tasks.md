# FDE document scaffold implementation plan

Goal: Deliver the local portion of #50 while retaining the blocked publication scope.
Architecture: `documentation/fde.py` owns local output and checks; CLI delegates.
Spec: [requirements](specs/fde-document-scaffold/spec.md) and [design](design.md).

- [x] 1. Write CLI regressions in `tests/test_fde.py` for hierarchy, exact dry run,
  refused overwrites/escapes, configuration, metadata errors and gate progression.
  Run `uv run --locked --no-sync pytest tests/test_fde.py -q` and confirm missing
  fde command failures before implementation.
- [x] 2. Add the YAML dependency explicitly; implement the service in
  `src/ai_dlc/documentation/fde.py` and thin `fde scaffold` / `fde check` commands.
  Re-run focused tests and fix until green.
- [x] 3. Document configuration and local commands in `docs/runbooks/fde-documents.md`,
  enroll catalog/code mappings, and update publication blocker in the existing
  team-document-publication proposal and local/shared knowledge design.
- [ ] 4. Run required checks, record docs impact against origin/main, validate and
  archive only this delivered specification. Leave #50 open and hand off commits
  for controller review without remote publication, merge or issue completion.
