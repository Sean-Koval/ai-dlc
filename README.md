# AI-DLC

AI-DLC keeps your development tools, project requirements, agent configuration, and working process in versioned, editable files. Python services power both the CLI and the local MCP server.

This checkout is a **v4 implementation candidate**. Native macOS Apple silicon bootstrap, a clean ARM64 devcontainer lifecycle, required checks on Linux x64/ARM64 and macOS Intel, Docker provider isolation, and read-only Linear sandbox health have been exercised. Factory-clean macOS, hosted cloud sessions, remaining live integrations, and release publication still require explicit walkthroughs. See [verification status](docs/release-verification.md). There is no published v4 bootstrap release yet.

## Prepare this checkout

From a checkout of this repository:

```sh
sh scripts/bootstrap.sh --source
```

The standalone script verifies and installs its pinned uv and mise downloads, prepares a private engine interpreter, installs the checked-out implementation, and prepares the project. It needs a POSIX shell, curl, CA certificates, tar, and standard platform utilities. It prints the two directories to add to your shell's PATH. It does not require preinstalled Python, Node, Rust, mise, or AI-DLC.

After adding those directories:

```sh
ai-dlc project check --required
ai-dlc doctor
ai-dlc setup plan --profile profiles/sean.toml
ai-dlc setup apply --profile profiles/sean.toml
```

Machine setup installs the selected workstation modules. Interactive sign-ins and provider workspace selections remain explicit. Configure Linear's team and native status IDs before publishing work. Keep vault paths and account choices in a machine TOML file, and supply it with `--machine` where supported. Credentials are environment references or native tool sign-ins.

Personal MCP servers declared in the selected profile are previewed by `setup plan` and merged into the supported user-level Codex and Claude configuration during `setup apply`. AI-DLC records only the entries it owns, preserves unrelated settings, and stops on edited or colliding entries. To review or apply only this layer, use `ai-dlc agents render --personal <profile> --check` and then replace `--check` with `--apply`.

## Prepare a project

```sh
ai-dlc project init my-project --preset python --apply
ai-dlc project adopt --root /path/to/existing-project --preset generic
```

Adoption previews changes; add `--apply` after reviewing the preview. It stages changes and refuses conflicting destination content. Generic, Python/uv, Node, and Rust presets include durable documentation and shared instructions. Versioned Git template sources support Copier updates; bundled development templates require an explicit versioned source before cross-machine updates.

The project owns `ai-dlc.toml` (setup, checks, gates and providers), `.mise.toml` (runtimes), `.ai-dlc/work/` (reviewed work bindings), and repository documentation. Machine configuration owns local paths. Personal notes remain in your existing Obsidian vault.

## Work cycle

1. Use discovery and specification skills to review scope and acceptance criteria. Record whether a formal specification is required.
2. Prepare `.ai-dlc/work/<id>.toml`; `work publish` creates or reuses the tracker item.
3. `work start` binds a branch. Implement, run `project check --required`, and update durable docs.
4. Finalize required specifications before review and merge.
5. `work finish` checks the merged revision's configured CI evidence and any deployment gate before completing the tracker item. Handoff failures remain separately retryable.

Linear, executable GitHub Issues, OpenSpec, GitHub SCM, Obsidian, and optional deployment evidence adapters are included. Configure the destination repository, workflow, target branch and provider settings explicitly. Provider changes affect new work; use reviewed rebind mappings for existing work.

## Architecture and customization

- `src/ai_dlc/`: configuration, provisioning, setup/check execution, workflow services, providers, CLI and MCP.
- `profiles/`, `modules/`, `targets/`: preferences, delegated installation recipes, target capabilities.
- `agents/`: shared skills, pinned sources, client capability declarations and owned configuration.
- `project-templates/`, `playbook/`, `contracts/`: Copier presets, development process, generated provider schemas.
- `docs/`: [architecture](docs/architecture.md), [workflow](docs/development-workflow.md), [migration](docs/migration.md), and [implementation record](docs/implementation-v4.md).

Local execution and GitHub Actions use one checks manifest. CI runs this checkout's implementation and publishes a receipt; completion checks verify workflow identity, merged SHA and manifest digests. Client hooks cover documented tool paths only. Repository merge rules must be configured by the repository owner.

The legacy `ai-dlc-cli scaffold --provider gemini` and `--all` interface remains available through Python. Rust source is retained for reference; Rust publishing is retired. See the migration guide for PATH conflicts.
