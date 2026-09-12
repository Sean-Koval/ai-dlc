# Retry Project membership readback before reporting uncertain attachment

## Context
Attachment is a mutation followed by an independent paginated readback over Project items. The mutation returns the item identity GitHub assigned, which is durable; the item connection is eventually consistent and can omit a just-created item. The adapter treated that single read as authoritative, so ordinary replication lag became an uncertain operation that blocked publication.

## Goals / Non-Goals
Separate replication lag from a genuinely uncertain attachment, and keep an unresolved readback failing visibly. Do not repeat the mutation, weaken the item-identity comparison, accept membership on the mutation response alone, or retry any other Project operation.

## Decisions
- Retry only the readback. The mutation is already idempotent for an attached issue, but re-sending it would widen the window in which two actors can disagree, and it is unnecessary once the item identity is known.
- Bound the retries and back off, so a persistently invisible item fails in bounded time rather than hanging a publication.
- Treat a different visible item identity as immediately terminal: it is a conflicting attachment, not lag, and waiting cannot resolve it.
- Keep `snapshot`'s existing ambiguity and identity errors, which propagate out of the retry loop unchanged.
- Rejected: trusting `addProjectV2ItemById` alone, which would let a misconfigured or cross-project response pass as verified membership. Rejected: an unbounded wait, which converts a remote outage into a hung command.

## Risks / Trade-offs
A genuinely failed attachment now costs the bounded backoff before it reports uncertainty. The bound is small relative to a publication, and the failure remains visible and uncertain rather than silently accepted.

## Migration Plan
No configuration or journal migration. An operation already recorded as uncertain is reconciled by the existing retry path.
