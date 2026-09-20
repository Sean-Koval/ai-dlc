## Why

The evaluation runner (#137) works, but its only driver is a script, so its reports
say nothing about whether AI-DLC helps. Issue #138 asks for real coding clients.
As written it is one very large delivery: two clients, multi-turn answers,
interruption and recovery, vault journeys, fake trackers, a fixture MCP server
and failure injection. None of that is worth building until one real client has
produced one honest treatment-versus-baseline comparison on one task.

## What changes

A first slice of #138, sized to produce that comparison:

- one real client driver, `claude-code`, run headless with its documented
  structured event stream, the same client version and model in both arms;
- the model API as the only reachable network destination, through an
  allow-listing proxy; attempts stay otherwise offline;
- a digest-pinned base image that has Git and the client, shared by both arms;
- a Git observer, so workflow assertions about what was committed, and in what
  order relative to the work record, can pass or fail instead of `unavailable`;
- usage (tokens, cost, turns) read from the client's stream into the report;
- one goal prompt per scenario, identical in both arms, with no commands, skill
  text or hints added.

## Out of scope

Codex, multi-turn declared answers and `needs-input`, interruption and
fresh-session recovery, vault journeys, fake tracker/SCM providers, the fixture
MCP server, process and MCP observers, failure injection, CI lanes. Each stays in
#138–#140 and is decided from the first comparison report.

## Impact

`src/ai_dlc/verification/evaluation/`, `contracts/evaluation/`, `evaluations/`,
the runbook. No change to product commands, provider conformance or skill
evaluation.
