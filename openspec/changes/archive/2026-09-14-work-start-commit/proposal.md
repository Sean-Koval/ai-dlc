# Collapse the delivery path: start commits its record and pr opens the pull request

## Why
Delivering issue #68, a ~60-line fix, took five commits and two pull requests. Two of the commits existed only because `work link` and `work start` edit the record file while `work start` refuses a dirty tree, and because the pull request was opened by hand and then linked back by hand. The gates are right; the steps between them should be one command each.

## What Changes
- `work start` and `work link` SHALL commit the record they edited, staging only `.ai-dlc/work/<id>.toml`, unless `--no-commit` keeps the previous behaviour.
- The SCM role contract SHALL gain an optional `pull_request_create` operation with payload `{title, body, base, head}` returning `{url, number}`; the GitHub adapter SHALL implement it through `gh pr create` and SHALL refuse a head branch without an upstream rather than pushing implicitly.
- `work pr <id>` SHALL render the pull request body from the record, open the pull request once, link its URL as the `pr` artifact and commit the record. A record that already carries a `pr` artifact SHALL be reported without creating another pull request, and a journaled creation SHALL NOT be repeated on retry.
- Delivery guidance SHALL describe the two-command path: `work start`, then `work pr`.

## Capabilities
### Modified Capabilities
- spec-delivery-traceability: start and link commit only their record; a pull request is opened exactly once and linked without a manual step.

## Impact
The work service, its CLI commands, the SCM contract models and generated schemas, the GitHub SCM adapter, the pure body renderer, delivery guidance and their tests. Publication, dependency checks, finish gates and the tracker adapters are unchanged.
