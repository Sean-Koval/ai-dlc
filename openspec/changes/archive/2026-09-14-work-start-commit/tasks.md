# Collapse the delivery path: start commits its record and pr opens the pull request

## Implementation
- [x] 1.1 Add the SCM contract operation `pull_request_create` with its payload and result models, regenerate `contracts/*.json`, and implement it in `GitHubSCM` through `gh pr create`, refusing a head branch without an upstream.
- [x] 1.2 Commit only the record from `work start` and `work link` with `--commit` on by default and `--no-commit` preserving the previous behaviour, with tests on a real temporary repository.
- [x] 1.3 Add `work pr <id>`: render the body from the record, journal and open the pull request once, link the URL and commit the record; an existing `pr` artifact prints and exits 0, with fake-SCM tests.
- [x] 2.1 Update delivery guidance, the GitHub provider instructions and the tool map (with template copies) to the two-command path.

## Verification and delivery
- [ ] 9.1 Record documentation-impact dispositions for the change.
- [ ] 9.2 Validate this OpenSpec change and run required project checks.
After delivery handoff, the integrator updates from the target branch, reviews and merges with fresh checks, verifies merged-revision CI receipts, then runs `ai-dlc work finish work-start-commit`. This is post-review integration, not an implementation task.
