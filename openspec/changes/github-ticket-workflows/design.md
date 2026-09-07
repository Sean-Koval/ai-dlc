## Authorized direction

GitHub Issues plus optional Projects v2 is the first implementation destination.
Retain the existing tracker create/find/read/transition/link contract instead of
renaming public operations to illustrative names from discussion. Add typed
capabilities; issue update/reopen semantics stay behind adapters and existing
terminal-transition gates. No new general tracker framework is necessary.

Capabilities use schema 1, lifecycle {in_progress: bool, closed: bool}, optional
operation names. Built-ins declare support in the registry; external adapters may
opt in explicitly. Unknown declarations/errors are not unsupported capabilities.
Legacy behavior is preserved only absent a declaration. Preserve binding hashes.

GitHub config adds optional project mapping (project id, status field id, mapped
open/in_progress/closed option ids). Guided discovery supplies IDs from named
resources. The issue's open/closed state and completion reason remain authoritative
for terminal behavior; project status describes planning. A configured in-progress
mapping enables the lifecycle capability. Invalid selected configuration fails.
Projects board-only Done never finishes work; finish still runs existing gates.

GitHub Projects uses GraphQL: attach an issue with addProjectV2ItemById, then use
updateProjectV2ItemFieldValue separately. Pagination and identity checks apply to
project items and fields. Preserve correlated issue creation and journal partial
outcomes; retry reads/reconciles instead of blindly creating. Validate terminal
issue state before changing planning state; verify post-write responses.
Source: https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects

Reuse existing scaffold/config ownership boundaries. Add an optional explicit
tracker choice and provider-neutral connection dispatch, retaining Linear wrappers.
GitHub discovery binds host/account/repository/project, complete fields/options and
freshness to the reviewed plan. Project-less setup remains valid. No secret values
or machine-specific paths in shared settings. Avoid agents.py until SAN-12 is
resolved; use existing gh/native tools and provider guidance first.

Migration uses configured adapters, never source/target name dispatch. Freeze old
effective defaults, verify explicit target references and preserve original aliases
and binding hashes. Remote-only backlog inventory remains a separate explicit
source when local work records do not cover all issues. Do not claim a whole
Linear backlog import from local records alone.

Plane/Jira adapter delivery remains in the parent plan; this child must not mark
that entire plan complete. No Plane install or Confluence access blocks GitHub.
