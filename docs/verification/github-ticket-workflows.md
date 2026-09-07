# GitHub ticket workflow qualification

Implementation branch: `codex/github-ticket-workflows`, based on planning commit
`0775b90`. Live and fixture evidence are recorded separately.

## Initial read-only environment inspection

On September 7, 2026, the installed CLI reported `gh version 2.95.0` (2026-06-17).
`gh api user --jq .login` returned `Sean-Koval`.
`gh project list --owner @me --format json` failed because the current credential
lacks `read:project`. No project/issue/configuration or authentication mutation
was performed. GitHub Projects read/write qualification is pending appropriate
local authentication, a selected repository and Project, and designated test data.
Do not claim project access from the successful account lookup.

The exact migration candidate mapping remains unreviewed. Local work records alone
cannot establish complete remote Linear active/planned inventory.

## Implementation evidence

Task and required-check results will be recorded here as they complete. No live
mutation or completed migration is established by mocked adapter responses.

Read-only local migration preparation inventoried 15 retained work records, 11
with tracker references. The ignored `.ai-dlc/local/github-adoption-inventory.json`
records unknown remote status and unverified destinations; it is not an executable
migration plan or a complete active/planned Linear backlog inventory.
