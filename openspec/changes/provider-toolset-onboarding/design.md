## Context

See the [source audit](../../../docs/planning/provider-toolset-code-audit.md).
Reuse schema-4 `roles`, provider aliases, `agents.servers`, existing module recipes,
component schema 1, and native client ownership. Do not create another plugin format.

## Decisions

Scaffold/adopt adds optional provider selections separate from language preset and
capability presence. Omitted selections preserve legacy defaults. Configuration
records selected provider aliases; shared provider choices override personal
preferences, and machine data supplies only local bindings under current scopes.

The optional documents/Confluence integration is deferred to #22, including
PT-05's former shared-knowledge guidance (now DP-07). It does not block current
tracker/native-client onboarding. Existing private Obsidian operations remain.

Introduce a small built-in definition registry containing component ID, supported
roles, connection discovery handler, and native connector defaults. Existing
integrity-verified custom components/providers continue to load. A custom provider
without an onboarding handler remains manually configurable with explicit
unsupported-onboarding output. No schema-1 component fields are silently added.

Shared connection service owns discovery result validation, saved non-secret
plan, source digest, selected alias/account/resource identity, project lock,
fresh remote revalidation and authored-file-safe apply. Provider handlers own
API discovery and valid selections, never arbitrary filesystem mutation.
Retain existing Linear command options/functions as compatibility wrappers.
Generic CLI selection fields are repeated `--select KEY=VALUE` arguments whose
keys/allowed choices come from that handler; unknown or ambiguous values fail.
Human users can choose returned names through their harness instead of UUIDs.

Native MCP rendering consumes reviewed server definitions through the existing
`agents.servers` boundary. Add client-specific transport mapping only where needed
for actual remote HTTP/stdio use. Remote OAuth belongs to native client sign-in;
local stdio uses inherited named variables. First delivery uses OAuth HTTP or
stdio, avoiding a new general secret-header templating system. Reviewed local
packages are pinned; neither a remote URL nor a desktop installation proves login.

Selecting a toolset composes a preview of shared provider settings, named modules,
server definitions, and guidance. Applying local configuration and rendering are
explicit steps using existing ownership rules. Conflicts fail before writes;
setup never deploys Plane's backend or changes remote projects. Connections selected
by multiple roles can share one server only when alias/account/endpoint
bindings are identical. Different account bindings never collapse by vendor name.

Obsidian component metadata describes existing-vault note operations; optional
GUI installation remains the existing explicit desktop module choice. GUI absence
in a container is reported as a viewing limitation, not a missing tracker dependency.

## Verification

The deferred custom-server inventory and selective shared-knowledge checks now
belong to team-document-publication; see the relationship design there.

Test two projects with different trackers/accounts on one machine, replay on a
second machine with a different vault path, authored config conflicts, no-network
render/check, missing OAuth, missing API credentials, invalid selections, stale
plans, and unchanged legacy Linear inputs. Live client recognition is a separate
gate from fixture rendering. Coordinate agents.py changes with SAN-12 before implementation.
