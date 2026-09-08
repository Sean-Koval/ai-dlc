## Context

AI-DLC currently treats the Obsidian vault as an isolated filesystem location configured via `paths.vault`. Note operations implemented in `src/ai_dlc/knowledge.py` use `os.walk(followlinks=False)` and validate every path via `inside()` in `src/ai_dlc/files.py`. Because `inside()` checks `path.resolve()` against the base directory, symlinked repositories inside `<vault>/Projects/` fail validation and are omitted from knowledge searches. Furthermore, creating project documentation symlinks is currently an out-of-band manual process.

See `proposal.md` for background motivation and `specs/obsidian-vault-linking/spec.md` for behavioral requirements.

## Goals / Non-Goals

**Goals:**
- Enable safe, opt-in symlink traversal inside `<vault>/Projects/` during knowledge operations so agents can query documentation from all linked active projects.
- Implement a dedicated `src/ai_dlc/vault_link.py` service and expose `ai-dlc project link-vault` CLI command.
- Support a `--docs-preset 5-pillar` option in project initialization and adoption that scaffolds `architecture/`, `adr/`, `specs/`, `runbooks/`, and `reference/`.
- Maintain strict safety against arbitrary path traversal or symlink loops.

**Non-Goals:**
- Implementing real-time file watching or desktop Obsidian plugin integration.
- Forcing existing AI-DLC core repositories to migrate to the 5-pillar documentation structure (it is an opt-in preset for user-built projects and MCPs).

## Decisions

### Decision 1: Controlled Symlink Following in `knowledge.py`
Instead of globally setting `followlinks=True` across the entire vault (which risks infinite recursion on cyclical symlinks), the walker will inspect entries directly under `<vault>/Projects/`. If an entry is a directory symlink, its target is verified to be a directory and canonicalized without escaping unauthorized host paths. A cycle detection set (`visited_inodes`) will prevent loops.
*Alternatives considered*:
- Global `followlinks=True`: Rejected because it risks cycles and traversing unintended symlinks outside `Projects/`.
- In-memory index table: Rejected because vault notes are file-backed and can change between runs.

### Decision 2: Native `ai-dlc project link-vault` Command
Create `src/ai_dlc/vault_link.py` encapsulating vault discovery from the machine configuration layer (`paths.vault`), symlink creation at `<vault>/Projects/<project_name>`, and `.gitignore` hygiene. Wire this into Typer under `@project.command("link-vault")`.
*Alternatives considered*:
- Keeping shell scripts in `bin/link-obsidian.sh`: Rejected because it fragments tooling and doesn't integrate with machine configuration.

### Decision 3: Opt-in 5-Pillar Documentation Preset
Provide `5-pillar` scaffolding within `src/ai_dlc/templates.py` or a dedicated helper. When selected, it creates:
- `docs/index.md` (Map of Content with Mermaid diagram)
- `docs/architecture/`
- `docs/adr/`
- `docs/specs/`
- `docs/runbooks/`
- `docs/reference/`
Existing files in `docs/` are never overwritten.
*Alternatives considered*:
- Enforcing 5-pillar across all repositories: Rejected because ops/engine repositories like AI-DLC itself follow a different doc taxonomy.

## Risks / Trade-offs

- [Risk: Symlink loops] → Mitigated by tracking visited realpath / inodes during recursive traversal.
- [Risk: Overwriting existing vault project symlink] → Mitigated by prompting or checking if target already points to the correct location; failing cleanly if pointing elsewhere without `--force`.
- [Risk: Corrupting git repository when modifying .gitignore] → Mitigated by atomic append with newline checking and deduplication.
