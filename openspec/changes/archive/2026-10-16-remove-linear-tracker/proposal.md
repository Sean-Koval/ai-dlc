# Remove Linear and document the tracker boundary with hangar

## Why

The owner and team use GitHub Issues, GitHub Projects and Jira Cloud, never Linear, yet a fresh install defaulted to Linear and roughly a thousand lines of Linear adapter, onboarding and conformance code remained to maintain. Hangar now owns tracker intake for agent jobs, so AI-DLC's adapters need a written boundary to avoid both tools transitioning the same ticket. Issues #199, #200 and #205.

## What Changes

- Default every new project, profile and template to the `github-issues` tracker; remove the Linear module, components entry, example credentials, Copier `LINEAR_API_KEY` default and this repository's Linear sandbox block.
- Remove the Linear adapter, its discovery/connection plans, `project rebind --connection-plan`, the `provider connect` `--organization`/`--team` flags and the Linear conformance target. A configuration that still selects Linear gets a typed refusal naming the supported trackers.
- Mark Plane unsupported: scaffolding requires `--allow-unsupported`; doctor reports it as unsupported and unqualified.
- Add `[work] tracker_writes = "finish-only"` so `work start` makes no tracker writes in repositories that also use hangar intake; document the tracker boundary.

## Capabilities

### New Capabilities

- `tracker-adapter-boundary`: TB-01 through TB-04.

### Modified Capabilities

- `linear-provider-onboarding`: retired as a whole. OpenSpec cannot archive a delta that removes every requirement, so its last text is preserved in `retired/linear-provider-onboarding-spec.md` in this change and `openspec/specs/linear-provider-onboarding/` is deleted.
- `native-work-harnesses`: NH-06 no longer lists Linear.
- `provider-connection-service`: PC-03 drops the Linear codec.
- `provider-toolset-onboarding`: PT-01 requires the Plane opt-in.
- `selective-tracker-migration`: TM-04 and TM-06 no longer name Linear.
- `toolset-composition`: TC-01 defaults to GitHub Issues.

## Impact

Existing projects keep the tracker their own configuration selects; Linear selections now refuse with migration guidance. Finished Linear-bound work records stay valid. Docs: README, architecture, tool map, roadmap, migration, development workflow, design notes and the docs catalog. No remote service is mutated.
