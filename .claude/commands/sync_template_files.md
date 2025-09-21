# Command: /sync_template_files

## Description
Synchronize the published embedded templates with the editable `templates/` source tree by running the repo helper script.

## Usage
```
/sync_template_files
```

## Steps
1. Confirm you are in the repository root (`ai-dlc`).
2. Run the sync helper:
   ```bash
   scripts/sync-cli-templates.sh
   ```
3. Inspect the output for rsync errors. The script should finish silently when the directories match.
4. Optionally validate the diff:
   ```bash
   git status --short crates/ai-dlc-cli/embedded-templates templates
   ```
5. If changes were expected, stage them for commit; otherwise investigate and rerun.

## Notes
- The script mirrors `templates/` into `crates/ai-dlc-cli/embedded-templates/`, ensuring `cargo install` bundles the up-to-date assets.
- Re-run after modifying any files under `templates/`.
- For CI automation, invoke the same script before packaging the crate or publishing to npm.
