# Remove Linear and document the tracker boundary: design

## Removal refusal

`ai_dlc.providers.REMOVED_PROVIDER_KINDS` maps `linear` to its guidance and `RemovedProviderError` (a `RefusedError`, exit status 2) carries it. `Registry.get` and `Registry.declares` call `refuse_removed_kind` after resolving the kind, so every lifecycle path that loads the tracker refuses before credentials or transport are used. `work start` consults `declares` first, so it refuses before branch or record changes. Connection setup, `plan_toolset` (init/adopt/sync answers) and rebind targets call the same helper; doctor reports it as a configuration gap. `provider_kind` itself does not raise, so read-only validation of finished records keeps working.

## Unsupported adapters

`ProviderDefinition.supported` defaults to `True`; Plane sets it to `False`. `plan_toolset(allow_unsupported=False)` refuses unsupported selections; the CLI exposes `--allow-unsupported` on `project init` and `project adopt`. Copier answer validation for `project sync` passes `allow_unsupported=True` because those answers were already chosen. Onboarding never selects a tracker, so it needs no flag.

## Finish-only tracker writes

`config.validate` accepts a `work` table on the base and project layers with only `tracker_writes` in `{"lifecycle", "finish-only"}`. `WorkService._start` keeps dependency reads and the capability declaration check, then under `finish-only` binds the branch and reads a linked ticket without publish, transition or comment. Finish is unchanged; its existing `reconcile_closed` path already treats an already-closed ticket as reconciled.

## Retained history

Finished work records pinned to `linear` stay untouched; `work validate --all` does not resolve their provider bindings. `.ai-dlc/migrations/*.json` and verification records keep their historical Linear evidence.
