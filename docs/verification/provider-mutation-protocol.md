# Live provider mutation qualification protocol

This is a prepared operator protocol for the remaining v4 release gate. No live
mutation run has occurred under this protocol. The existing conformance runner's
`--live` option remains a read-only health check; its result cannot satisfy this
gate. Offline adapter fixtures are a separate evidence class.

## Required run declaration

Before creating anything, record the exact source commit, engine and provider
versions, image digest, platform, sandbox account and project/repository identity,
authorized operation list, run identifier and evidence directory. Use only an
explicitly designated disposable destination. Inject credentials through the
existing local secret mechanism; shared manifests and evidence contain references,
not values. Jira qualification uses new work only. Plane remains optional for
GitHub users. No Linear request is required for the current personal workflow.

For each selected deployment, record its actual capabilities, required creation
fields, configured transition meanings, account permissions and supported recovery
lookup. If these are unavailable, record the missing input and stop before writes.
Do not invent a universal lifecycle mapping from one provider's configuration.

Use the existing sandbox isolation path with exact-host egress policy and retained
preflight evidence. A direct host adapter call or namespace without enforced egress
does not qualify this release gate. An operator may prepare a run-specific script
using the existing provider and journal contracts once the destination declaration
is reviewed; this protocol does not add a second development harness or silently
extend the read-only runner.

The current sandbox launcher hardcodes the read-only conformance entrypoint,
mounts fixtures read-only and uses an ephemeral work directory. It cannot yet run
this mutation protocol unchanged. Before writes, review a run-specific launch
entrypoint, persistent private journal/evidence placement and the exact interruption
boundary. Reuse the enforced network topology/preflight; do not silently change
`--live`. Durable state must survive the container loss being tested. This execution
preparation remains pending with the destination declaration; the protocol alone
is not a runnable mutation-conformance implementation.

## Observations to retain

1. Read the declared account/project and compare exact identities before mutation.
2. Create one run-correlated disposable item through the selected provider contract.
   Retain the requested payload digest and response identity. Read it back and
   verify destination, correlation and content. Never infer ownership from a title.
3. Repeat the same journaled intent and prove that no duplicate item is created.
   In an explicitly controlled interruption case, retain uncertainty and reconcile
   the original correlation before any retry. Absence that cannot be established
   authoritatively stays uncertain.
4. Exercise declared supported updates/transitions with read-back. Preserve the
   distinction between completed, cancelled, open and in-progress. Record unsupported
   transitions as unsupported; they do not become successful remote mutations.
5. Verify AI-DLC completion rejects missing or mismatched specification/PR/CI
   evidence. An adapter lifecycle observation is not a completed AI-DLC work cycle.
   Qualify a full work cycle separately with real matching finish evidence.
6. Verify close/reopen behavior only for the declared disposable item and permitted
   transitions. Retain final item identities and states. No source migration or
   deletion is part of this protocol; any later cleanup is separately explicit.

Record requests with secrets removed, timestamps, correlation/journal state,
canonical reads, transport interruption boundaries, terminal state and failures.
Do not label synthetic transport errors as a real service outage. Independent
review must distinguish actual service observations, controlled local interruption,
fixture checks and unrun cases. A partial run remains partial.

## Current missing inputs

Actual work Jira policy/site/project/workflow and a selected Plane deployment,
version and disposable account/project have not been supplied. The broader release
gate also retains its configured native/cloud and evaluation requirements. This
protocol prepares execution; it does not authorize company mutations, install Plane,
publish a release, or mark parent issues #14, #17, #20 or #21 complete.
