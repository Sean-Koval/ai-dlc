# Pin the workflow plugin in a team harness

A team harness repository holds the native files a team's agents run with and a
hangar `harness.lock` that pins them; the
[example team harness](https://github.com/Sean-Koval/team-harness) is a copyable
one, and its
[ai-dlc workflow plugin section](https://github.com/Sean-Koval/team-harness#the-ai-dlc-workflow-plugin)
shows the result. ai-dlc publishes the [workflow plugin](workflow-plugin.md) into
it; the harness repository decides where the plugin is on. These steps use the
example's names (`harnesses/team-default`, marketplace `team-harness`).

1. **Publish, dry run first.** From a prepared ai-dlc checkout
    (`sh scripts/bootstrap.sh --source`), with the harness repository checked out
    beside it:

    ```sh
    uv run --locked --no-sync python scripts/publish_workflow_plugin.py \
      --harness-repo ../team-harness/harnesses/team-default \
      --marketplace team-harness --dry-run
    ```

    The dry run writes nothing. It lists the files it would copy and prints the
    component ids and digests, the source commit and the marketplace entry; a
    harness that already has this revision reports `"status": "unchanged"`. Repeat
    with `--apply` to write `plugins/team-harness/ai-dlc-workflow/` and
    `native/codex/ai-dlc-workflow/`. The script refuses a target that holds anything
    other than an unmodified earlier publication.

2. **Open a pull request in the harness repository** with those files. The first
    time, add the printed marketplace entry to
    `plugins/team-harness/.claude-plugin/marketplace.json`; the script never edits it.

3. **Pin it in the lock.** Re-pin with the harness repository's tooling:
    `hangar harness freeze` from a good run, or the example's
    `python scripts/relock.py harnesses/team-default --write` for a hand edit. The lock
    gains one component, with the printed source commit as its `source`:

    ```yaml
    - id: plugin:ai-dlc-workflow@team-harness
      digest: sha256:…   # hangar's plugin digest, printed as hangar_plugin_digest
      path: plugins/team-harness/ai-dlc-workflow
      enabled: true
      source: git:https://github.com/Sean-Koval/ai-dlc#plugins/ai-dlc-workflow@<commit>
    ```

    Keep `plugins: {autoUpdate: false}` in the lock, so the treatment can't change
    mid-experiment.

4. **Point `candidate` at it.** In `channels.yaml`, set the harness's `candidate` to
    the new `harness_digest` that `hangar harness check` prints. `stable` stays where it
    is: only a promotion after flightdeck's with/without comparison moves it.

Every file the script publishes, the plugin README included, is in the plugin's
`plugin.lock.json` and in hangar's plugin digest. Any change to
`plugins/ai-dlc-workflow/` therefore gives the harness a new candidate when it is republished.

hangar pins and mounts `plugin:` components since
[hangar#221](https://github.com/Sean-Koval/hangar/issues/221); consuming this plugin
from the team harness repository is tracked in
[hangar#139](https://github.com/Sean-Koval/hangar/issues/139).
