## Context

The user-approved v4 design defines a local orchestrator, not a hosted agent queue.
The implementation uses narrow services for configuration, filesystem management,
project preparation/checks, provider operations, workflow completion and knowledge.
Typer and the official MCP SDK call the same services.

## Decisions

- Bootstrap uv and its Python interpreter live separately from mise project tools.
- Self CI executes the checked-out package; release installs require hashed artifacts.
- Check receipts are evidence only when retrieved from a matching authenticated run.
- Copier owns project template revisions and answers; agent providers own their sections.
- SQLite journals record uncertainty, but remote correlation/state reconciliation is required.
- OpenSpec completion requires the archive to be present in the clean merged checkout.
- Hooks cover declared payload paths. CI/services retain durable enforcement.
- No live sandbox, cloud, release or skill-evaluation claim is inferred from fixture tests.

## Remaining verification

See docs/release-verification.md for target walkthroughs, sandbox networking, live
provider operations, publishing constraints, and behavioral skill evaluation evidence.
