# Native connection composition verification

This child implements PT-03 through `ai-dlc agents connect`: explicit reviewed role
bindings compose into the project's existing native server configuration. Its
base is the immutable toolset candidate `1904e9c`, including the reviewed common
connection primitives and native rendering dependency. Subsequent toolset review
repairs and parent archive moves are integrated separately by the root coordinator.

The input/plan format and behavior are specified in
[the child spec](../../openspec/changes/native-tool-composition/specs/native-tool-composition/spec.md).
[The runbook](../design/native-tool-composition.md) includes an actual local
AI-DLC MCP-service binding and the separate native rendering step. No provider
MCP defaults, endpoint URLs, authentication or lifecycle adapter are fabricated.

## Test-driven evidence

The initial 23 focused cases failed because the new module did not exist. After
implementation, authored multiline arrays exposed an unsafe one-line edit and a
real enrolled-profile regression exposed copying personal server defaults into
shared configuration. Those regressions failed before their corrections. The
fixture's explicit XDG cache is isolated, alongside its configuration/state/home.

The final focused suite passed 30 tests. It exercises exact alias/account/transport
deduplication with both roles retained; differing transports/accounts; declared
accounts across two projects sharing an endpoint; role/provider/account/source,
input and saved-plan changes; real machine account overrides; personal-default
exclusion; single-line and multiline inline arrays plus array-table preservation;
symlink refusal; binding edits during apply; and real CLI preview/save/apply followed
by the existing renderer. An authored native conflict is preserved through config
apply and rejected by the separate renderer. Common plan persistence is reused;
its existing provider-specific schema validation remains unchanged.

These are synthetic local configuration fixtures, not live service or native-client
consumer qualification. No skill changed, and no separate skill-consumer result is
claimed. The bindings declare expected accounts; fixtures cannot prove that an
endpoint-shared OAuth cache switched identity, that a GUI recognized files, or that
a service account has access. Config-only apply explicitly reports rendering
pending and authentication unverified.

## Remaining delivery

Independent review, dependency integration, parent archive/roadmap reconciliation
and exact merged-revision verification are root-owned delivery steps. Existing
manual native definitions remain compatible outside explicitly requested
composition. Unfamiliar authored TOML representations are refused rather than
rewritten without proven equivalence.

## Required checks

All five required checks passed: generated assets, format, lint, types, and the
full **1,239-test** suite. Strict OpenSpec validation also passed. The
[receipt](native-tool-composition/local-checks.json) records the dirty candidate
based on `1904e9c`; source, tests and assets stayed frozen during this passing run.
Evidence prose and task checkmarks were finalized afterward. No remote service
state changed and no review, archive or merged-revision result is implied.
