# Validate work record artifact references as a repository invariant

## Implementation
- [x] 1.1 Classify a repository-anchored suffix-less specification reference as local regardless of whether the path exists, with regression tests for a moved change directory, a never-written anchored path, an opaque slash ID and a provider URI.
- [x] 1.2 Share one artifact validator between the dependency-closure reader and a repository-wide reader that validates record shape, local artifacts and the graph without resolving bindings, with regression tests.
- [x] 1.3 Add `ai-dlc work validate --all`, offline and journal-free, accepting exactly one of a work ID or `--all`, with CLI tests.
- [x] 2.1 Run the repository-wide validation as the required `work-records` check here and in the project template.
- [x] 2.2 Update delivery guidance for the anchored classification and the repository-wide check.

## Verification and delivery
- [x] 9.1 Record documentation-impact dispositions for the change.
- [x] 9.2 Validate this OpenSpec change and run required project checks.
- [x] 9.3 Update from the target branch, review the pull request, merge with fresh checks and verify merged-revision CI receipts.
