# Plane tracker

Use the shared AI-DLC work lifecycle with a configured `kind = "plane"` tracker.
Plane is optional; other trackers do not require a Plane server or token.

Select Cloud or self_hosted explicitly. Self-hosted HTTP is supported only for
localhost or literal loopback IPv4/IPv6 addresses, with valid explicit ports.
Non-loopback deployments require HTTPS. API and web origins are separately
reviewed configuration; the adapter never follows redirects.

Credentials are named environment references. Choose `api_key` for X-API-Key or
`oauth_bearer` for externally managed OAuth. Native client login is separate.
Use common `provider connect` discovery, `--select KEY=VALUE`, saved plan and
`--apply` to review account/workspace/project and distinct lifecycle state IDs.

The adapter writes correlation in visible escaped description text and the same
create request's external pair. Preserve both. It patches only state and adds
exact-URL links without replacing authored descriptions or link titles.
Cancellation never satisfies successful completion; work finish gates still apply.

Every mutation requires trusted local invocation context and an immutable durable
intent before sending. If a response is lost, a later attempt only reads for an
exact result; unresolved absence or duplicate evidence remains blocked. Inspect
the operation in Plane and retain local state. There is no force-retry/reset
command. New machines, relocated roots, removed state or new operation IDs do not
inherit prior intent knowledge. No cross-machine exactly-once guarantee is made.

This adapter is verified against HTTP transport fixtures and a recorded public
source contract, not a live Plane instance, edition, deployment or tracker swap.
Do not install Plane, migrate work, or assert live qualification from these fixtures.
