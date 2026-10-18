# Contributing

Read [AGENTS.md](AGENTS.md) for repository boundaries and [the documentation
map](docs/design/documentation-map.md) for authoritative sources. AI-DLC ships Python; the
retired Rust implementation survives only as archived plans and git history.

AI-DLC is feature-frozen; [ADR 0001](docs/decisions/0001-refocus-ai-dlc.md) lists
what stays active. Changes outside the in-scope list are closed with a pointer;
bug fixes in frozen areas are welcome.

1. Start from the current roadmap and the linked GitHub issue. Read the relevant
   OpenSpec requirements before changing behavior. Keep formal change artifacts
   together in OpenSpec.
2. Prepare the checkout with `sh scripts/bootstrap.sh --source`. Use an isolated
   branch and add regression tests for observable changes.
3. Follow the [source map](docs/architecture.md#source-layout). Put durable docs
   in their existing home, update the catalog and record documentation impact.
4. Run `ai-dlc project check --required` and strict OpenSpec validation. Review
   generated changes and preserve authored content.
5. Describe the behavior, verification and remaining limits in the pull request.
   After merge and exact-revision CI, complete tracked work with `ai-dlc work finish`.

Portable skills live in `agents/` and project scaffolding in `project-templates/`.
Generated client copies are not independent sources of truth.

This repository does not commit rendered skill copies (`[agents] skills = []` in
`ai-dlc.toml`), so `.claude/skills/` and `.agents/skills/` stay empty here. Load the
team skills from the workflow plugin while working on AI-DLC. The plugin is off by default
(`defaultEnabled: false`), so enable it for the session:

```sh
claude --plugin-dir plugins/ai-dlc-workflow --settings '{"enabledPlugins":{"ai-dlc-workflow@inline":true}}'
```

`claude plugin list` with the same two flags should show the plugin as loaded:

```text
  > ai-dlc-workflow@inline
    Status: √ loaded
```

Without `--settings` it reports `Status: × disabled` and no skills load.

Codex contributors read the same skills from `plugins/ai-dlc-workflow/skills/`.
Edit skills only under `agents/skills/`, then run
`python scripts/build_workflow_plugin.py` to refresh the plugin. Repository layout checks apply to AI-DLC itself; downstream projects
retain their chosen structure.
