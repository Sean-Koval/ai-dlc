## Context and decisions

Retain tracker operations `create`, `find`, `read`, `transition`, and optional
`link`. Normalize `state` for workflow decisions and retain `native_state` and
remote identifiers as response metadata. Add optional read-only `capabilities`
with a versioned response describing supported lifecycle intents and optional
operations. New Plane/Jira adapters implement it; existing external adapters
without it keep the legacy transition path and are reported as capability-unverified.
Built-in Linear and GitHub Issues declare their actual semantics. The workflow
service consumes capabilities, not provider names. Completion stays exclusively
in the gated WorkService path.

Registry definitions declare support for capability discovery before it is
invoked. An existing extension with no declaration uses the legacy path; an
opted-in provider with a failed or malformed capability response fails visibly.
Never reinterpret network or authentication failure as lack of capability support.

Use httpx and existing environment credential injection for the narrow adapters.
Native MCP connections remain independently usable by the harness. Adapter code
must not depend on a credential cached inside a particular desktop application.
No new SDK or generic MCP transport engine is required for the lifecycle path.

Plane settings bind instance URL, workspace, project, API credential reference,
and configured start/closed states. Require a supported deployed API version and
complete pagination. Map work items into the existing normalized contract.
Implement durable correlation through supported external identifiers or a
lossless marker field verified against the target edition. Never rely on HTML
comments surviving a service editor without round-trip evidence.

Jira Cloud settings bind site/cloud ID, project, issue type, API authentication
references, required field defaults and lifecycle state policy. Discovery resolves
names and required create fields. Query currently allowed transitions for each
issue; a destination status is not a transition ID. Require exactly one compatible
transition or an explicit configured transition preference. Validate required
transition fields, post-read the resulting state, and keep cancelled distinct from
successful closed work. Do not guess resolution values.

Jira correlation uses an exact durable marker/property strategy whose lookup is
verified for the selected project and permissions. Paginate project-scoped reads
when search cannot prove complete reconciliation. A search timeout, partial
result, duplicate marker, or unavailable property lookup never means absence.
No blind create retry after uncertain writes. Retry bounded read failures where
safe; let existing journals retain uncertain mutations. Review endpoint origins
and prevent credential-bearing redirects to another origin.

## Scope boundary

Deliver the existing lifecycle only. General issue editing, sprint management,
comments, search, and exploration remain upstream tools. Endpoint discovery and
status mapping use the shared onboarding service. Live mutation qualification uses
explicit disposable projects, separately from existing read-only provider health.
The adapter test must prove a fixture provider with a new ID runs the same service
without adding another vendor branch. Do not generalize unrelated SCM behavior.
