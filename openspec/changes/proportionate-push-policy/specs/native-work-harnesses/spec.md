## ADDED Requirements

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
