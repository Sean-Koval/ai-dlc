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

### Requirement: NH-05 Offline next-step summary

`ai-dlc next` SHALL derive each work record's lifecycle state from its local artifacts alone and print a plain-text summary naming the state and the next command per record, the required checks and the check command, and stating that the tracker was not consulted. A record without a `tracker` artifact is `unpublished`; with a tracker and no `pr` it is `in progress`; with a `pr` and a specification under `openspec/changes/` outside `openspec/changes/archive/` it is `awaiting merge, archive first`; with a `pr` and an archived specification, or no required specification, it is `awaiting merge`. Unpublished records SHALL appear only with `--all`. `--json` SHALL return a JSON list of records with exactly `id`, `state`, `tracker`, `pr` and `next` fields. `ai-dlc context --brief` SHALL print the same text, `ai-dlc context` SHALL keep its machine-readable output, and the session-start hook SHALL include the first ten lines of the summary.

#### Scenario: A record has no tracker artifact
- **WHEN** the summary reads a record whose artifacts have no `tracker`
- **THEN** the record is `unpublished` with `next: ai-dlc work publish <id>`, and it is printed only with `--all`

#### Scenario: A record is published but has no pull request
- **WHEN** a record has a `tracker` artifact and no `pr` artifact
- **THEN** the record is `in progress` with `next: ai-dlc work pr <id>`

#### Scenario: A pull request exists and the change is not archived
- **WHEN** a record has a `pr` artifact and its `spec` is under `openspec/changes/` but not under `openspec/changes/archive/`
- **THEN** the record is `awaiting merge, archive first` with the archive command as its next step

#### Scenario: A pull request exists and the change is archived
- **WHEN** a record has a `pr` artifact and its `spec` is archived or `requires_spec` is false
- **THEN** the record is `awaiting merge` with `next: ai-dlc work finish <id>`, and the header states that the tracker was not consulted rather than guessing whether the record is finished

#### Scenario: The summary makes no remote calls
- **WHEN** `ai-dlc next` runs with an empty `PATH` and no network
- **THEN** it exits 0 in under one second, reads only the repository tree, and its JSON form is the requested list of record objects

#### Scenario: A session starts
- **WHEN** the session-start hook runs in a project whose records can be read
- **THEN** the returned context contains the first ten lines of the summary, and when the project cannot be read the context falls back to the plain instruction

### Requirement: NH-06 Capability-scoped shared project guidance

Generated shared project guidance SHALL derive workflow instructions from the
project's existing selected roles and runtime provider kinds. It SHALL retain
configuration/documentation guidance and every configured required check in
declared order with its command, existing missing-command reporting and the
required project-check command. Generic specification, tracker and knowledge
instructions SHALL apply only to their selected roles. Concrete OpenSpec archive
instructions SHALL apply only to the OpenSpec runtime provider. Built-in merge
instructions SHALL apply only to supported selected GitHub SCM. Built-in finish
instructions SHALL apply only with both supported selected GitHub SCM and a
selected built-in Linear, GitHub Issues, Jira Cloud or Plane tracker; OpenSpec
merged-checkout recovery SHALL additionally require OpenSpec. Required
documentation-gate follow-up instructions SHALL apply only when that gate is
configured as required and merge guidance applies.

Provider-kind aliases and existing `kind`/`type` resolution precedence SHALL match
runtime resolution. Component metadata alone SHALL NOT establish executable
provider capabilities. Rendering SHALL remain offline and SHALL NOT execute
provider adapters or weaken required checks, finish gates or ownership rules.
Provider/bundle/team guidance and authored material SHALL retain their existing
delivery and preservation contracts; selected native clients SHALL receive
equivalent conditional shared guidance.

#### Scenario: Local-only adoption
- **WHEN** a project selects no specification, tracker or SCM role and configures a required check
- **THEN** generated guidance retains configuration, durable documentation and verification instructions, reads an active work record only if present, and omits specification/tracker authority, archive, merge and finish directives
- **AND** it does not claim that local validation completes a tracker lifecycle

#### Scenario: Partial adoption retains only applicable instructions
- **WHEN** OpenSpec is selected without tracker or SCM
- **THEN** specification and archive guidance is present without a merge premise, finish command or merged-checkout recovery
- **WHEN** a built-in tracker and GitHub SCM are selected without a specification role
- **THEN** tracker, merge and finish guidance is present without OpenSpec archive or checkout instructions
- **WHEN** OpenSpec and GitHub SCM are selected without a tracker
- **THEN** specification, archive and merge guidance is present without a finish command or finish checkout instruction

#### Scenario: Full supported delivery retains its safeguards
- **WHEN** OpenSpec, GitHub SCM and any of Linear, GitHub Issues, Jira Cloud or Plane are selected
- **THEN** generated guidance includes specification finalization, tracker authority, archive before merge, pre-merge required checks, work finish and the merge-checkout recovery instruction
- **AND** an empty configured finish-gate list does not suppress the existing mandatory runtime gates or advertise weaker completion

#### Scenario: Custom specification provider is not OpenSpec
- **WHEN** a selected custom specification provider supplies component guidance, including a custom runtime provider that reuses the OpenSpec component
- **THEN** generated shared prose retains generic specification/provider instructions but contains no OpenSpec archive command or OpenSpec checkout recovery directive
- **AND** custom linked guidance is not rewritten

#### Scenario: Runtime aliases determine applicable built-in behavior
- **WHEN** providers select supported built-in runtime kinds through aliases with `kind` or legacy `type`
- **THEN** their shared instructions match the corresponding built-in selections, with `kind` taking precedence over `type`, and component IDs do not override runtime identity

#### Scenario: An extension owns its lifecycle instructions
- **WHEN** a tracker or SCM selection resolves to a custom component without the corresponding built-in runtime kind
- **THEN** its generic role guidance and component links remain available but shared prose does not invent built-in finish support or GitHub merge support for that custom SCM
- **AND** rendering does not execute that extension to discover support

#### Scenario: Documentation gate is optional but declared checks are not
- **WHEN** an applicable merge configuration changes between having and not having a required documentation gate
- **THEN** stale-document-disposition advice appears only with the required gate while every declared required check and its command remains present in both configurations

#### Scenario: Re-rendering narrows only owned instructions
- **WHEN** an intact generated full-delivery section is re-rendered after the project removes provider selections
- **THEN** only inapplicable owned instructions are removed, authored prefix/suffix and required checks are preserved, selected clients receive equivalent updated guidance, and a second render is unchanged
- **AND** an authored edit inside the managed section continues to refuse before writes

### Requirement: PPP-01 Explicit project-owned push policy

The optional bound-push hook SHALL support project-only `agents.bound_push_policy` values `all-branches` and `tracked-branches`; omission SHALL mean `all-branches`. Configuration from personal, machine or team-source layers SHALL NOT set or weaken this field. Invalid types, unsupported values or forbidden-layer settings SHALL fail visibly before rendering policy-bearing configuration or allowing a covered operation. Selecting this policy SHALL NOT enable an otherwise unselected hook.

#### Scenario: Existing configuration omits policy
- **WHEN** a project selects bound-push without declaring its policy
- **THEN** its strict all-branches behavior is unchanged and an unbound covered push remains denied

#### Scenario: Project explicitly chooses lightweight mode
- **WHEN** the project declares `agents.bound_push_policy = "tracked-branches"`
- **THEN** the bound-push hook applies the lightweight policy only within its existing supported payload and client coverage

#### Scenario: Local or imported configuration tries to waive policy
- **WHEN** a personal, machine or team-source layer supplies bound_push_policy
- **THEN** configuration is rejected rather than overriding or supplying the project policy

### Requirement: PPP-02 Tracked branches retain complete local validation

For both policy modes a covered operation on a branch associated with a work record SHALL require one or more associated records, each locally valid and reviewed with a tracker reference and valid local provider bindings. A branch association SHALL remain tracked when its record is unreviewed, missing a tracker or otherwise invalid. Any invalid matching record, unreadable inventory that prevents determining association, malformed policy and unavailable branch identity SHALL deny the operation with a specific remedy. Hook inspection SHALL remain offline and SHALL NOT create operation journals, tracker items or substitute work records.

#### Scenario: A tracked record is not ready
- **WHEN** a covered push occurs under either mode and its matching record is unreviewed, invalid, lacks a tracker reference or has provider-binding drift
- **THEN** the hook denies the push and names the failing local condition without treating the branch as unbound

#### Scenario: Complete association cannot be determined
- **WHEN** a record cannot be read sufficiently to establish whether it binds the current branch
- **THEN** the hook denies the covered operation with an inventory remedy and does not assume an exemption

#### Scenario: A valid tracked branch is ready
- **WHEN** one or more locally valid reviewed tracker-bound records match the known current branch and every matching record has valid local bindings
- **THEN** the covered nondestructive operation passes this hook's binding check without remote tracker inspection

#### Scenario: A delivery branch has several valid work items
- **WHEN** multiple reviewed tracker-bound records with valid local bindings associate with the same branch under either policy mode
- **THEN** their count alone does not deny the operation and every matching record is validated
- **AND** adding one unreviewed or invalid matching record causes denial without changing valid records

### Requirement: PPP-03 Lightweight allowance applies only to truly unbound branches

With explicit tracked-branches policy, the hook SHALL allow a covered nondestructive operation when a complete readable local record inventory establishes that the known current branch has no associated work record. With all-branches policy it SHALL continue denying that operation. The allowance SHALL NOT depend on a path, branch-name, commit-size or risk heuristic, create a per-branch waiver record, or weaken required checks, native approval, SCM review or finish gates.

#### Scenario: A lightweight change has no associated record
- **WHEN** an explicitly opted-in project has a known branch with no matching record after complete inventory and receives a direct nondestructive push or PR-create payload
- **THEN** the hook allows that operation without manufacturing a work record and explains the selected lightweight policy

#### Scenario: An apparently small tracked change is invalid
- **WHEN** only documentation changed but a matching record is unreviewed
- **THEN** the hook denies the operation under both modes regardless of changed-file appearance

#### Scenario: An unbound force push is attempted
- **WHEN** a destructive command recognized by the existing classifier is attempted on an unbound branch in tracked-branches mode
- **THEN** the existing destructive-operation denial remains in effect

### Requirement: PPP-04 Guidance states the selected policy and its limits

Applicable generated and canonical guidance SHALL distinguish strict all-branches policy from explicit tracked-branches policy and describe which lightweight path each permits. It SHALL preserve the declaration that only supported native hook payloads are covered and that the hook does not establish remote tracker state, arbitrary-terminal enforcement or completion evidence. Configurations without bound-push SHALL NOT acquire a new record requirement merely from this setting.

#### Scenario: Strict hook and small-change guidance coexist
- **WHEN** a selected client is configured with bound-push in default mode
- **THEN** its applicable guidance states that covered publication still requires a reviewed tracker-bound record even where the general workflow permits a record-free PR

#### Scenario: Hook is not selected
- **WHEN** policy is valid but no selected client requests bound-push
- **THEN** rendering preserves the existing no-hook behavior and does not advertise hook enforcement

