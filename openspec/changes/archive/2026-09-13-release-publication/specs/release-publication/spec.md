## ADDED Requirements

### Requirement: RP-01 Tag-driven publication of verified assets
A release SHALL be published only from a Git tag whose version equals the engine version, through the release workflow. The workflow SHALL build the wheel and locked hashed constraints, verify wheel installation and scaffolding against those constraints, generate the hash-bound manifest with the release download directory as its base URL, and publish exactly those verified assets together with their digests. A manual workflow run SHALL produce only a candidate artifact and publish nothing.

#### Scenario: A matching tag is pushed
- **WHEN** a tag `v<version>` is pushed and `<version>` equals the engine version in `pyproject.toml`
- **THEN** the workflow publishes the wheel, the constraints, the manifest and a checksum file whose digests equal the manifest's, and the manifest's URLs point at that release

#### Scenario: A tag does not match the engine version
- **WHEN** a tag is pushed whose version differs from the engine version
- **THEN** the workflow fails before any asset is uploaded

#### Scenario: The workflow is run by hand
- **WHEN** the workflow is dispatched manually with a base URL
- **THEN** it uploads a candidate artifact to the run and creates no release, tag or public asset

### Requirement: RP-02 The manifest travels with generated projects
Release-mode bootstrap SHALL retain the sourced manifest beside the installed engine. Project generation SHALL include `bootstrap/release.sh` from the running engine's retained manifest, byte for byte, subject to the same conflict and authored-file protections as template files, and SHALL report whether the manifest was included. A source-installed engine SHALL report that no manifest is available rather than generating a project that claims one.

#### Scenario: A release-installed engine generates a project
- **WHEN** `ai-dlc project init` or `adopt --apply` runs from an engine installed by release-mode bootstrap
- **THEN** the project contains `bootstrap/release.sh` identical to the retained manifest and the result reports the manifest as included

#### Scenario: A source-installed engine generates a project
- **WHEN** generation runs from a source environment
- **THEN** no `bootstrap/release.sh` is written, the result reports the manifest as absent, and the project's release-mode bootstrap keeps refusing with its existing message

#### Scenario: A bare install directory bootstraps in release mode
- **WHEN** release-mode bootstrap runs in a directory holding only the bootstrap files and a minimal `ai-dlc.toml`, with no `.mise.toml`
- **THEN** the engine installs and project setup completes without attempting to activate tools the directory does not declare

#### Scenario: A generated project bootstraps in release mode
- **WHEN** the generated project's `scripts/bootstrap.sh` runs without `--source`
- **THEN** it downloads and verifies the wheel and constraints named by the included manifest, installs the engine and runs project setup

### Requirement: RP-03 Release evidence states its boundary
Release documentation SHALL describe the publication procedure and SHALL distinguish workflow verification, clean-environment installation proof and remaining unqualified obligations, without representing a local stand-in host or a fixture as a published release.

#### Scenario: A release cycle is recorded
- **WHEN** release evidence is added to the verification record
- **THEN** it names the revision, the environment, the host that served the assets and which outstanding obligations the run satisfied or left open
