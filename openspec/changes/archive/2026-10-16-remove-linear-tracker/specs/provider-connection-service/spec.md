## MODIFIED Requirements

### Requirement: PC-03 Legacy connection compatibility
Existing GitHub interfaces and saved formats SHALL retain their codec, freshness and recovery guarantees. Generic repeated `--select KEY=VALUE` SHALL validate provider keys and conflict with duplicate legacy selections before discovery; apply SHALL consume only its saved selections.

#### Scenario: The removed Linear interface is requested
- **WHEN** a caller requests a Linear connection or names a provider whose kind is `linear`
- **THEN** the service refuses with the typed removal guidance before discovery, credential use or any write

#### Scenario: A GitHub default Project plan is applied
- **WHEN** an existing reviewed GitHub schema is selected
- **THEN** existing exact-byte/work/runtime checks, exclusive save and Project creation journal remain in force
