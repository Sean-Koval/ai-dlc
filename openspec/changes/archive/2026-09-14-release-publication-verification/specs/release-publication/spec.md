## MODIFIED Requirements

### Requirement: RP-01 Tag-driven publication of verified assets
A release SHALL be published only from a Git tag whose version equals the engine version, through the release workflow. The workflow SHALL build the wheel and locked hashed constraints, verify wheel installation and scaffolding against those constraints, generate the hash-bound manifest with the release download directory as its base URL, and publish exactly those verified assets together with their digests. A manual workflow run SHALL publish nothing, including when dispatched at a tag. With no existing-tag replay selection, it SHALL produce only a candidate artifact. With an explicit existing published tag, it SHALL skip packaging and publication and run read-only consumer verification against the unchanged published assets.

#### Scenario: A matching tag is pushed
- **WHEN** a tag `v<version>` is pushed and `<version>` equals the engine version in `pyproject.toml`
- **THEN** the workflow publishes the wheel, the constraints, the manifest and a checksum file whose digests equal the manifest's, and the manifest's URLs point at that release

#### Scenario: A tag does not match the engine version
- **WHEN** a tag is pushed whose version differs from the engine version
- **THEN** the workflow fails before any asset is uploaded

#### Scenario: The workflow is run by hand
- **WHEN** the workflow is dispatched manually with a base URL
- **THEN** it uploads a candidate artifact to the run and creates no release, tag or public asset

#### Scenario: An existing published tag is replayed
- **WHEN** a maintainer manually selects an existing published tag for verification
- **THEN** packaging and publication are skipped, the tag is passed as quoted data to asset downloads, and all three consumer platforms initialize the seed and generated project before explicit CI freshness checks

#### Scenario: Manual dispatch uses a tag workflow ref
- **WHEN** a manual candidate or replay dispatch selects a tag as its workflow ref
- **THEN** it cannot publish, replace or delete a release or tag

#### Scenario: Normal publication fails or verification is cancelled
- **WHEN** a tag-push package or publish job fails, or the workflow is cancelled
- **THEN** consumer verification does not run as if publication had succeeded

### Requirement: RP-03 Release evidence states its boundary
Release documentation SHALL describe the publication procedure and SHALL distinguish workflow verification, clean-environment installation proof and remaining unqualified obligations, without representing a local stand-in host or a fixture as a published release.

#### Scenario: A release cycle is recorded
- **WHEN** release evidence is added to the verification record
- **THEN** it names the revision, the environment, the host that served the assets and which outstanding obligations the run satisfied or left open

#### Scenario: A verification harness failure is replayed
- **WHEN** existing published assets are verified with a corrected workflow
- **THEN** the record retains the original tag, asset source commit and failed run, names the replay workflow commit and run separately, and claims only observed platform outcomes without changing the original run result
