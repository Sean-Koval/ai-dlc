# Workflow plugin

`plugins/ai-dlc-workflow/` is one optional Claude Code plugin: the workflow
guidance as a skill, ten more skills and hooks that work without the `ai-dlc` CLI.
A team harness can pin it as a single component and run with or without it. It is
off by default (`defaultEnabled: false`). Try it locally:

```sh
claude --plugin-dir plugins/ai-dlc-workflow \
  --settings '{"enabledPlugins": {"ai-dlc-workflow@inline": true}}'
```

`scripts/build_workflow_plugin.py` generates the directory from `agents/skills/`
and the shared guidance, and records component digests in `plugin.lock.json`. The
`generated` check fails when it is stale. The hooks need `python3`.

The same build emits a Codex form in `native/codex/`: identical skills, a Codex
`hooks.json`, an `AGENTS.fragment.md` and a `.codex-plugin` manifest.
`scripts/publish_workflow_plugin.py --harness-repo PATH --marketplace NAME --dry-run|--apply`
copies both into a team harness for a with/without comparison.

The
[plugin README](https://github.com/Sean-Koval/ai-dlc/blob/main/plugins/ai-dlc-workflow/README.md)
covers contents, the Codex spike, the A/B arms, hangar limits and how to turn it off.
