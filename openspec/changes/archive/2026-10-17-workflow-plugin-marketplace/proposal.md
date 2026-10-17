# Publish the workflow plugin into hangar's directory-marketplace layout

## Why

hangar#221 made harness locks pin a plugin at `plugins/<marketplace>/<source>`, with
its entry in `plugins/<marketplace>/.claude-plugin/marketplace.json`, and digest it
over that entry. `scripts/publish_workflow_plugin.py` still wrote
`plugins/ai-dlc-workflow/`, which current hangar rejects. Follow-up to
[#193](https://github.com/Sean-Koval/ai-dlc/issues/193).

## What Changes

- `publish_workflow_plugin.py --marketplace NAME` publishes the Claude plugin to
  `plugins/NAME/ai-dlc-workflow/`, reports the harness's existing entry (or a
  `./ai-dlc-workflow` suggestion) and hangar's plugin digest. Without the option the
  previous layout is kept.
- The plugin README and Get started describe the option.

## Capabilities

### Modified Capabilities

- `workflow-plugin`: WP-07 gains the marketplace layout.

## Impact

Harness maintainers re-publish with `--marketplace`. The harness keeps owning its
`marketplace.json` and `harness.lock`.
