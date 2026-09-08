## Why

PT-03 still needs a usable path from reviewed provider-role/native-account bindings to existing project `agents.servers`. Native renderers consume manual entries today; toolset scaffolding does not compose them.

## What Changes

- Add `ai-dlc agents connect` preview/saved-plan/config-only apply using explicit reviewed native bindings.
- Deduplicate only exact server alias, declared account and transport identity; refuse ambiguous alias conflicts and stale role/provider/account/input/source identity.
- Reuse common exclusive plan and exact configuration writer boundaries; native rendering stays a separate explicit step.

## Capabilities

### New Capabilities
- `native-tool-composition`: Compose reviewed project native bindings without changing authentication or provider lifecycle semantics.

### Modified Capabilities
None. Existing manual agents.servers rendering, component schema 1, owned native files and remote provider operations retain their contracts.

## Impact

CLI registration, a bounded composition service, reusable common plan-reading primitive, tests and runbook. No default upstream URL, new secret-header representation, installation, OAuth login, machine/global client write or live qualification.
