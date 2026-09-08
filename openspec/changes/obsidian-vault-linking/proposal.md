## Why

Projects in AI-DLC require bidirectional integration with Obsidian vaults. Currently, `knowledge_find` explicitly skips symlinks within vaults, preventing agents from indexing and retrieving documentation from symlinked project documentation trees (`Projects/<name>`). Furthermore, linking a repository's `docs/` folder into an Obsidian vault currently requires ad-hoc bash scripts rather than a first-class AI-DLC CLI command with automatic `.gitignore` safeguards and agent rules configuration.

## What Changes

- Add safe symlink traversal to `src/ai_dlc/knowledge.py` and `src/ai_dlc/files.py` so notes under symlinked directories (e.g. `Projects/<name>`) within the configured vault can be discovered and indexed without path escaping vulnerabilities.
- Add `ai-dlc project link-vault` CLI command (and `--link-vault` option to `project init` and `project adopt`) that resolves the machine's `paths.vault`, symlinks `<project>/docs` to `<vault>/Projects/<name>`, updates `.gitignore` with `.obsidian/` and `.trash/`, and records the link metadata.
- Introduce an opt-in `5-pillar` documentation preset for project scaffolding and adoption (`docs/index.md` Map of Content, `architecture/`, `adr/`, `specs/`, `runbooks/`, `reference/`).
- Ensure non-destructive project adoption when a repository already has an existing `docs/` directory.

## Capabilities

### New Capabilities
- `obsidian-vault-linking`: Manages bidirectional project documentation linking into Obsidian vaults, safe symlink traversal in knowledge operations, and the 5-pillar documentation structure.

### Modified Capabilities
<!-- None: existing capability requirements remain backward-compatible -->

## Impact

- `src/ai_dlc/knowledge.py`: Update note scanning and path validation to safely traverse symlinks within the vault.
- `src/ai_dlc/files.py`: Refine `inside()` helper to safely permit canonical symlink targets when explicitly authorized.
- `src/ai_dlc/cli.py`: Expose `@project.command("link-vault")` and `--link-vault` flag.
- `src/ai_dlc/templates.py`: Support `5-pillar` documentation preset.
- Automated tests in `tests/test_knowledge.py` and `tests/test_vault_link.py`.
