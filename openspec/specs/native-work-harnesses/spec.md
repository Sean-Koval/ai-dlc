# native-work-harnesses Specification

## Purpose
Distribute owned project guidance and workflow bundles across selected native harnesses with client-specific transports and honest readiness reporting.
## Requirements
### Requirement: NH-01 Native project guidance
An explicitly selected Antigravity client SHALL receive the selected skills in
`.agents/skills` and a project rule in `.agents/rules/ai-dlc.md` containing the
same configured provider and verification guidance as other supported clients.
Native activation metadata outside its managed rule body SHALL survive updates.
Codex and Antigravity sharing the skills directory SHALL yield one consistent
owned set. Unselected clients and authored material SHALL be preserved.

#### Scenario: Two clients share portable skills
- **WHEN** Codex and Antigravity are selected together
- **THEN** repeated rendering is idempotent and both reference the same skill contents without duplicate ownership or deletion

#### Scenario: An authored native rule exists
- **WHEN** the rule conflicts with the proposed owned configuration
- **THEN** rendering refuses before any write and leaves the authored rule intact

### Requirement: NH-02 Client-specific MCP transport
Project remote HTTP definitions SHALL use Claude Code's `type=http` plus `url`
and Antigravity's `serverUrl` in its `.agents/mcp_config.json`. Stdio definitions
SHALL preserve command and arguments. Owned changes SHALL preserve unrelated
servers and refuse edited owned or conflicting authored entries before writes.

#### Scenario: A previously owned Claude remote entry needs its type
- **WHEN** rendering updates an unchanged owned remote entry produced by the prior version
- **THEN** its HTTP type is added while unrelated authored server definitions remain unchanged

#### Scenario: Remote authentication is needed
- **WHEN** an OAuth remote definition is rendered
- **THEN** no credential values are persisted and client login remains a separate explicit action

#### Scenario: Antigravity environment expansion is unqualified
- **WHEN** a server requires generated environment-name interpolation for Antigravity
- **THEN** rendering reports that unsupported mapping before writes instead of copying secret values or inventing a native expansion format

### Requirement: NH-03 Honest client readiness
Offline inspection SHALL distinguish generated guidance from actual installed
client recognition and authentication. Antigravity hook requests without a
qualified capability fixture SHALL refuse. Configuration presence SHALL NOT be
reported as live qualification, native login, or runtime completion enforcement.

#### Scenario: Antigravity guidance is rendered offline
- **WHEN** readiness inspects the generated project files without a live client session
- **THEN** it reports file delivery independently and retains client recognition/login as unverified with a native activation/check action

#### Scenario: A work repository uses different tools
- **WHEN** it selects its own provider aliases and project settings
- **THEN** rendering uses only that repository's effective shared selections and does not copy the engine repository's personal tracker/account binding

### Requirement: NH-04 Shared native workflow-bundle distribution
Selected vendored workflow skills SHALL use the same registered native client directories as packaged skills. Clients sharing a directory SHALL share one owned export, and an explicit native-client render SHALL update or remove that client's owned bundle exports without adopting retained backups.

#### Scenario: Antigravity uses a selected bundle
- **WHEN** Antigravity is selected alone or alongside Codex and a vendored skill bundle is rendered
- **THEN** the skill is available in `.agents/skills`, no unselected Claude copy is created, and readiness uses the same directory mapping

#### Scenario: A native-only render removes an old bundle
- **WHEN** an owned bundle is deselected and Antigravity is explicitly rendered
- **THEN** its obsolete shared skill export leaves active guidance and its retained backup is reported under the existing non-deleting transaction contract

