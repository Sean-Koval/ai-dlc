## 1. Defaults (#199)

- [x] 1.1 Switch the base profile, template defaults, Copier answers and example profiles to `github-issues`; remove the Linear module, components entry and this repository's Linear sandbox block.
- [x] 1.2 Add tests for default init output, Copier output without `LINEAR_API_KEY` and `work validate --all` without `[providers.linear]`.

## 2. Adapter removal (#200)

- [x] 2.1 Delete the Linear adapter, guidance, runbook, onboarding codec, connection-plan rebind and conformance target.
- [x] 2.2 Add the typed removal refusal and its tests, including `work start` exit status.
- [x] 2.3 Mark Plane unsupported with the `--allow-unsupported` scaffold opt-in and doctor reporting.

## 3. Tracker boundary (#205)

- [x] 3.1 Document the hangar boundary, collision rule and kept adapters.
- [x] 3.2 Add `[work] tracker_writes = "finish-only"` with validation and a recording-provider test; test reconciled finish on an already-closed ticket.

## 4. Delivery

- [x] 4.1 Update affected docs and the catalog, record documentation dispositions and run `ai-dlc project check --required`.
