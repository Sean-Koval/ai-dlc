## ADDED Requirements

### Requirement: EER-01 Compatible scoped reporting
Existing machine status and doctor defaults SHALL retain their contracts. Opt-in `machine status --root PATH --export FILE` and doctor `--effective-environment` SHALL produce the same schema-1 safe local projection, distinguishing desired state, observed state and unknowns without network access, provider-health execution or client model sessions. Executable version probes SHALL require explicit `--probe-versions`; default reporting SHALL use known metadata and mark unavailable observations unknown.

#### Scenario: Default status is used
- **WHEN** a user invokes machine status without export/compare options
- **THEN** existing enrollment output and behavior remain compatible

#### Scenario: A scoped observation is unavailable
- **WHEN** the requested project's cache is corrupt or an explicitly requested version probe times out
- **THEN** the export includes the scoped reason and unknown value, retains independent results and does not infer readiness or run repairs

### Requirement: EER-02 Engine and configuration provenance
Reports SHALL separately identify current-process and PATH-selected engine version/provenance, release/source/unknown installation kind, known source revision, dirty state and artifact digest, pinned profile/source identities, desired and observed runtime/client edition/version, portable configuration and managed-guidance digests. A shared package version SHALL NOT establish equal source identity.

#### Scenario: Release and source both identify as 0.4.0
- **WHEN** two exports share the package version but have different known source or artifact identities
- **THEN** comparison reports blocking engine drift; missing provenance instead produces unknown comparability

#### Scenario: Same source commit has local edits
- **WHEN** one export records a dirty source checkout at the same revision as the other
- **THEN** comparison cannot report reproducible engine parity and exposes the dirty-source limitation

### Requirement: EER-03 Safe bounded export and deterministic identity
Schema-1 export SHALL use the allowlisted fields, canonical JSON identities, ordering and limits defined in the design. It SHALL omit secrets, credential values, private paths, account identities, raw commands, repository URLs, shell content, global client state and chat history. Digests SHALL cover only defined nonsecret projections or verified nonsecret provenance; unsafe or unestablished digest inputs SHALL yield null with a reason, not a hash of excluded bytes. Existing destination files SHALL be refused. Authentication presence and evidence-backed verification SHALL remain separate.

#### Scenario: Local configuration includes secrets and private locations
- **WHEN** export reads selections whose raw sources include token-bearing URLs, private paths, environment values or arbitrary commands
- **THEN** only safe projected IDs/statuses/digests are emitted, with no raw values or secret-derived digest, and invalid identifiers are redacted with a bounded reason code

#### Scenario: Two reports differ only in export time
- **WHEN** the desired and observed allowlisted fields are identical but observation timestamps differ
- **THEN** configuration and observation identities match while timestamps remain visible outside those identities

#### Scenario: Native evidence populates recognition status
- **WHEN** otherwise identical report data gains evidence-backed recognition or authentication status
- **THEN** those evidence-derived fields remain outside observation identity so the evidence does not invalidate its own context binding

#### Scenario: Authentication was never verified
- **WHEN** credentials are locally present without valid scoped authentication evidence
- **THEN** verification remains not-assessed even if configuration, rendering and runtime availability are healthy

### Requirement: EER-04 Precise offline comparison
`machine status --compare LEFT RIGHT` SHALL read only two bounded schema-compatible exports and produce logical-field findings classified as blocking, expected-platform, informational or unknown. Missing required identity SHALL prevent a parity conclusion. Platform compatibility SHALL derive from selected component metadata; version compatibility SHALL derive from declared constraints/adapters rather than guessed equivalence.

#### Scenario: Supported operating systems differ
- **WHEN** exports otherwise agree and each selected component explicitly supports both recorded operating systems
- **THEN** OS differences remain visible as expected-platform findings without claiming identical environments

#### Scenario: Guidance or required runtime diverges
- **WHEN** an observed managed-guidance digest differs from desired or a required observed runtime violates its declared constraint
- **THEN** comparison reports blocking drift and the existing repair/check route without mutating either machine

#### Scenario: Unknown or malformed export
- **WHEN** an input has an unsupported schema, duplicate ID, unknown field, invalid type or exceeds 1 MiB
- **THEN** comparison exits 2 with a bounded safe error and never follows paths, executes commands or quotes raw private input

### Requirement: EER-05 Evidence identity and limits
Reports SHALL expose configuration and observation identities suitable for binding native evidence, with explicit completeness limitations. A changed client version/edition, platform, engine provenance, selected source/configuration or managed guidance SHALL change the relevant identity and prevent reuse of exact-context evidence. Fixture success SHALL NOT establish live client/platform qualification.

#### Scenario: Client upgrades after smoke observation
- **WHEN** a later report observes a different selected client version
- **THEN** observation identity changes and previous exact-context native evidence is stale even if the version difference is declared compatible

#### Scenario: Portable identity matches across independent homes
- **WHEN** two machines have the same allowlisted portable state and different private bindings
- **THEN** their configuration identities match without exporting private bindings or claiming copied authentication or global client state
