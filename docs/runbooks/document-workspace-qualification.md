# Document workspace qualification walkthrough

Repeat document organization and native workspace qualification on a disposable
copy of the controlled messy project. Record what you observe in the
[documentation workflow verification record](../verification/documentation-workflow.md).
Automated fixture tests do not replace this walkthrough, and this walkthrough does
not qualify another host, client or platform.

## Prepare disposable inputs

From an AI-DLC source checkout:

```sh
uv run --locked --no-sync python tests/fixtures/messy_project.py /tmp/ai-dlc-qualification/project
mkdir -p /tmp/ai-dlc-qualification/vault
```

Use a new vault directory, never a personal vault. The builder commits a small
Parcel service with scattered root, `docs/`, `legacy/` and OpenSpec documents plus
one Git-ignored scratch file. Its `EXPECTED_REVIEW_POINTS` list what a reviewer
checks afterwards. Do not give that list or a move plan to the harness under test.

## Organization exercise

1. Start a fresh harness session in the fixture with the shipped
   `document-organize` skill available.
2. Ask for an outcome, such as "organize this project's scattered docs", without
   file-by-file instructions.
3. Review its proposal before any edits. Confirm it read content through inventory
   and bounded review packets, not only file names.
4. Let it apply the reviewed plan. Inspect the Git diff against each review point:
   preserved rationale, the retained ADR convention, labelled history, an unchanged
   OpenSpec file, repaired links and no `docs/specs/` tree.
5. Run `ai-dlc project docs-check` in the fixture. Record remaining findings and any
   corrections the reviewer had to make.

## Native workspace exercise

1. From the fixture root, preview and then apply
   `ai-dlc project link-vault --mode mount --vault /tmp/ai-dlc-qualification/vault`.
2. Run `ai-dlc project workspace-check`. Confirm connected mounts, classified links
   and `native_client` reported as `not-assessed`.
3. Open the vault in Obsidian and observe: navigation from a document to the
   OpenSpec specification, search across both folders, backlinks, an Obsidian edit
   appearing in `git diff`, and an external repository edit refreshing in an open
   editor.
4. Restore the fixture's baseline bytes and confirm `git status` is clean.

## Record the result

Add a dated section to the verification record with the host, client version,
fixture revision, observed behavior and failures. Keep automated fixture results,
the harness exercise and native client observations as separate evidence. Leave
work-computer, Antigravity and other platform checks pending until someone actually
performs them.
