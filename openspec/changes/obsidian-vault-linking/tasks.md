## 1. Safe Symlink Knowledge Traversal

- [ ] 1.1 Update `src/ai_dlc/files.py` to allow safe canonical path validation for authorized symlink targets and verify behavior with unit tests.
- [ ] 1.2 Update `src/ai_dlc/knowledge.py` to safely traverse project directory symlinks under `<vault>/Projects/` with cycle protection and verify note discovery via `knowledge find`.

## 2. Vault Link Service and CLI Command

- [ ] 2.1 Implement `src/ai_dlc/vault_link.py` to resolve the machine's `paths.vault`, establish `<vault>/Projects/<name>` symlinks, and ensure `.gitignore` ignores `.obsidian/` and `.trash/`.
- [ ] 2.2 Expose `@project.command("link-vault")` in `src/ai_dlc/cli.py` and verify CLI help and execution.

## 3. 5-Pillar Documentation Preset

- [ ] 3.1 Implement 5-pillar scaffolding (`architecture/`, `adr/`, `specs/`, `runbooks/`, `reference/`, and `index.md` Map of Content) in project templates without overwriting existing docs.
- [ ] 3.2 Wire `--docs-preset` option into `ai-dlc project init` and `ai-dlc project adopt` and verify with non-destructive adoption test.

## 4. Integration Verification and Test Suite

- [ ] 4.1 Add unit and integration tests in `tests/test_vault_link.py` and test symlinked knowledge indexing in `tests/test_knowledge.py`.
- [ ] 4.2 Run full test suite via `uv run pytest` and verify all checks pass.
