# provider-connection-service Specification

## Purpose
Expose declared provider connection capabilities through common reviewed discovery and configuration plans while preserving legacy connections and explicit delivery limits.
## Requirements
### Requirement: PC-01 Declared connection capability
Trusted definitions SHALL declare kind, roles and supported named selections. Guided connection SHALL resolve the configured alias/kind without provider branches in the CLI. A missing handler SHALL report unsupported setup without changing lifecycle capability or configuration.

#### Scenario: A third provider supplies discovery and patch selection
- **WHEN** a trusted definition registers a complete named resource discovery and non-secret patch selector
- **THEN** the existing CLI discovers, previews, saves and applies through the common service without a vendor-specific CLI branch or provider-owned filesystem writer

### Requirement: PC-02 Exact reviewed common plans
The common service SHALL own exclusive saved-plan storage and authored-safe apply for declarative handlers, binding provider/account identity, complete discovery, canonical resource IDs, exact source bytes, effective runtime and retained work. Apply SHALL rediscover and reject changed or incomplete evidence before mutation.

#### Scenario: A named resource becomes ambiguous
- **WHEN** a requested resource name matches multiple resources or discovery is incomplete
- **THEN** preview refuses without saving a plan or changing configuration

#### Scenario: A saved selection drifts
- **WHEN** source, runtime, account, resources, work bindings or patch differs at apply
- **THEN** common apply refuses rather than rewriting the plan or guessing a new selection

#### Scenario: Configuration has authored or bound state
- **WHEN** apply would change a bound tracker identity or cannot represent the patch while preserving authored TOML
- **THEN** it refuses and leaves configuration intact

### Requirement: PC-03 Legacy connection compatibility
Existing Linear and GitHub interfaces and saved formats SHALL retain their codec, freshness and recovery guarantees. Generic repeated `--select KEY=VALUE` SHALL validate provider keys and conflict with duplicate legacy selections before discovery; apply SHALL consume only its saved selections.

#### Scenario: Linear names are selected
- **WHEN** organization, team and state names or IDs uniquely identify authorized resources
- **THEN** preview saves existing canonical IDs, preserving state-type validation and the canonical-digest/comment-only apply policy

#### Scenario: A GitHub default Project plan is applied
- **WHEN** an existing reviewed GitHub schema is selected
- **THEN** existing exact-byte/work/runtime checks, exclusive save and Project creation journal remain in force

### Requirement: PC-04 Honest delivery scope
Shared connection evidence SHALL distinguish deterministic discovery/file tests from live qualification and SHALL NOT claim native client authentication, Jira lifecycle support or completion of the mixed-scope onboarding parent.

#### Scenario: Only a synthetic provider is exercised
- **WHEN** common service conformance passes with fixture discovery and real local files
- **THEN** evidence describes fixture/local validation and leaves actual tenant/client qualification pending

