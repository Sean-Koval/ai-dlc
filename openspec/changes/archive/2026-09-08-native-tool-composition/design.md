## Context and approved boundary

Root approved explicit binding-to-existing-agents.servers composition after reviewing PT-03. This child starts from immutable toolset candidate 1904e9c. Its CLI is `ai-dlc agents connect --root . --bindings docs/setup/native-bindings.toml --save-plan .ai-dlc/local/native-plan.json`, followed by `--apply-plan .ai-dlc/local/native-plan.json`. Apply updates shared configuration only; native render remains pending and protects authored files separately. No cross-file atomicity or prospective native-file preflight is claimed.

## Input and identity

The new bounded input artifact uses `schema=1` with repeated `[[bindings]]`, separate from component metadata. Each binding has role, provider, server alias and non-secret expected account, plus either URL or command/args/environment-variable names. Explicit reviewed transport is the initial supported setup path; no upstream connector defaults or URLs are fabricated. ProviderDefinition role metadata is respected where declared; explicitly configured custom providers remain compatible with manual transport selection.

The provider must match the effective selected role. A configured provider account alias must match the requested expected account. An absent provider account reference is recorded as absent, not silently assigned; the binding's native account remains a declared expectation and authentication stays unverified. Source/runtime/input fingerprints bind both absence and configured account/resource changes. Machine credentials and global client files are never written.

Identity includes exact alias, expected account, transport kind and endpoint or command/ordered args/environment names. Identical requests deduplicate; a reused alias with a differing identity refuses before writes. Existing manual aliases must match exactly to be reused; ambiguous missing account metadata on a requested alias requires explicit review rather than assuming its logged-in identity. Unrequested manual entries and source comments remain unchanged. Configured roles are not rewritten, so each role retains its provider guidance.

## Apply and ownership

Use the common exclusive saved-plan writer and guarded exact configuration apply primitive, adding a reusable safe plan reader without changing its existing provider-plan validator. Before applying, recompute the complete plan from current input/runtime/project bytes and compare it with the saved reviewed plan. The exact writer rechecks the source/runtime/input snapshot under its lock before replacement. The renderer remains a separate command; a successful configuration apply reports rendering and native authentication pending.

Native OAuth caches may be shared by endpoint across projects or aliases. A server alias/account expectation does not switch or verify the logged-in user. Separate project configuration is retained, but the user must inspect/authenticate the intended identity in each native client. No live isolation or successful login is inferred from fixtures.

## Verification

TDD covers exact dedup, conflicting account/transport refusal, same endpoint across distinct projects, role/provider/account/input/source drift, saved-plan tampering, manual source preservation, symlink refusal, and real CLI preview/apply followed by existing owned rendering. Required checks and strict OpenSpec validation precede independent review. Fixtures and local checks do not establish native client recognition or service qualification.
