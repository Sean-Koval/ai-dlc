## ADDED Requirements

### Requirement: TR-05 Provider identity excludes evidence policy
A provider identity fingerprint SHALL cover the configuration that determines which external service, branch and workflow runs a work record was reviewed against. It SHALL NOT cover receipt artifact policy, which the finish gate authenticates from the merged manifest rather than from the binding. An SCM configuration key that is not recognised evidence policy SHALL contribute to identity. Canonical delivery guidance SHALL describe this boundary without claiming the fingerprint authenticates receipts.

#### Scenario: The CI receipt matrix changes
- **WHEN** the configured receipt artifact names change and a work record holds bindings from before the change
- **THEN** mutation proceeds without a binding drift refusal, and the finish gate still requires every receipt named by the merged manifest

#### Scenario: The trusted repository, branch or workflow changes
- **WHEN** the configured SCM repository, target branch or workflow changes
- **THEN** mutation refuses with provider binding drift until the record is reviewed again

#### Scenario: An unrecognised SCM setting changes
- **WHEN** an SCM configuration key that is not recognised receipt artifact policy is added or changed
- **THEN** mutation refuses with provider binding drift rather than treating the unknown setting as evidence policy

#### Scenario: Guidance describes the boundary
- **WHEN** a person or agent reads canonical delivery guidance on configured evidence and bindings
- **THEN** it states that the receipt matrix does not drift bindings and does not claim the fingerprint authenticates receipts
