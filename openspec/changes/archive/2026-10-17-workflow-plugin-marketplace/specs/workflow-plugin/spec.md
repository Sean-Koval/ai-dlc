## MODIFIED Requirements

### Requirement: WP-07 Publication into a harness directory

`scripts/publish_workflow_plugin.py --harness-repo PATH` SHALL copy the Claude plugin without `native/` to `PATH/plugins/<marketplace>/ai-dlc-workflow/` when `--marketplace` names one, else to `PATH/plugins/ai-dlc-workflow/`, and the Codex form to `PATH/native/codex/ai-dlc-workflow/`, and print the component ids and digests to pin, including hangar's plugin digest over the marketplace entry when a marketplace is named. `--dry-run` SHALL write nothing. It SHALL refuse when a target holds files that the previous publication's lock does not record or whose digests differ, and SHALL never write outside the two targets.

#### Scenario: An empty harness
- **WHEN** `--dry-run` runs against an empty directory
- **THEN** it lists the files and component ids and writes nothing

#### Scenario: Apply twice
- **WHEN** `--apply` runs and then runs again
- **THEN** the first writes the files and the second reports no change

#### Scenario: A hand-edited target
- **WHEN** a published file was edited in the harness
- **THEN** `--apply` refuses and leaves the file as it is

#### Scenario: A directory marketplace
- **WHEN** `--apply` runs with `--marketplace team` against a harness whose `plugins/team/.claude-plugin/marketplace.json` lists the plugin
- **THEN** the plugin lands in `plugins/team/ai-dlc-workflow/`, the marketplace file is unchanged, and the reported plugin digest equals hangar's
