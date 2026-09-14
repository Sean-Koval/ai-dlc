## ADDED Requirements

### Requirement: TR-06 One command between delivery gates

`work start` and `work link` SHALL commit the record they edit, staging only `.ai-dlc/work/<id>.toml`, unless the caller disables the commit. `work pr <id>` SHALL open the pull request for the bound branch through the SCM role exactly once, render its body from the record, link the resulting URL as the `pr` artifact and commit the record. The SCM adapter SHALL refuse to open a pull request for a branch without an upstream and SHALL name the remedy rather than pushing implicitly.

#### Scenario: Start commits only its record
- **WHEN** reviewed work is started on a clean checkout
- **THEN** the working tree is clean afterwards and the newest commit is `chore(work): start <id>` touching only `.ai-dlc/work/<id>.toml`

#### Scenario: A pull request is opened once
- **WHEN** `work pr` runs for a started record on a pushed branch and runs again afterwards
- **THEN** the first call creates one pull request, links its URL and commits the record, and the second call prints the existing URL without sending another create

#### Scenario: The branch has no upstream
- **WHEN** `work pr` runs for a branch that has not been pushed
- **THEN** it refuses with the remedy to push the branch first, creates no pull request and changes no record
