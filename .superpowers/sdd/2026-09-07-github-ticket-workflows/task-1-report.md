# Task 1 report: capability contract and work start

## Outcome

Implemented GT-01 without changing provider binding fingerprint construction or
the reviewed-work and finish-gate paths.

- Added the optional `capabilities` wire operation and generated schema 1 response:
  lifecycle support for `in_progress`/`closed` plus extensible optional operation
  names.
- Added registry declarations for built-in Linear and GitHub Issues providers,
  explicit operation opt-in for registered providers, and validated external
  configuration declarations.
- Added truthful built-in capability responses. Linear derives lifecycle support
  from configured status IDs; issue-only GitHub reports no in-progress lifecycle
  state and does report close support.
- Changed `WorkService.start` to query declared capabilities before local branch or
  ticket mutations. Unsupported in-progress state preserves the existing
  unsupported transition response and reads the ticket unchanged. A declared
  query/validation failure propagates. Only an absent declaration uses the legacy
  transition and reports `verified: false`.
- Left Task 2's Projects behavior and proposed `prepare` operation unimplemented;
  `optional_operations` intentionally accepts future operation names.

## TDD evidence

RED:

- Capability/start selection: 3 expected failures. `Registry.register` rejected
  the new `operations` argument, and legacy start omitted the unverified marker.
- External declaration validation: 1 expected failure because a string-valued
  declaration was incorrectly accepted.

GREEN:

- `pytest -q tests/test_providers.py`: 24 passed.
- `pytest -q tests/test_workflow.py -k 'start or provider_workspace_drift or unknown_gate or empty_gates or finish'`:
  15 passed, 35 deselected.
- `pytest -q tests/test_providers.py tests/test_workflow.py`: 74 passed.

## Quality checks

- Generated schema check: passed after regenerating `contracts/manifest.json` and
  the capability request/response schemas.
- Ruff format check for all changed Python files: passed.
- Ruff lint for all changed Python files: passed.
- Pyright for all changed production Python files: 0 errors, 0 warnings.
- The repository-required aggregate check passed generated, format, lint, and
  types. Its full test phase was intentionally cancelled at 59% on coordinator
  direction because the final child-wide check will supersede it.

## Scope and concerns

- No live provider calls were made; provider semantics are fixture/offline tested.
- The unsupported response retains its `supported` and `reason` shape while using
  provider-neutral wording for every declared tracker capability.
- Unrelated documentation/spec edits already present in the shared worktree were
  left unstaged and are not part of the Task 1 commit.

## Follow-up: provider-neutral unsupported reason

An integration review found that the unsupported transition reason still named
GitHub Issues when an arbitrary declared provider lacked in-progress support.
Regression assertions for both the GitHub fixture and arbitrary `fake` provider
failed against that wording, then passed after replacing it with the generic
`Tracker does not support the in_progress lifecycle state` message. The response
shape remains unchanged.
