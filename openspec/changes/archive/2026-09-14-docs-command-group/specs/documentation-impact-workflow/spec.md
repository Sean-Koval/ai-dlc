## MODIFIED Requirements

### Requirement: DI-01 Scoped impact inspection
A shared CLI and MCP service SHALL inspect a Git comparison plus current working content, match optional catalog code, requirement and verification references, and expose changed unmapped files. Reads SHALL stay inside the repository. The CLI SHALL expose the documentation workflow under one `ai-dlc docs` group whose commands are exactly `check`, `review`, `gate`, `read`, `search` and `init`; impact inspection, disposition recording, baseline proposal, review-packet preparation and review validation SHALL be modes of `ai-dlc docs review`. Each former `ai-dlc project docs-*` command SHALL keep working for one release as a hidden alias that runs the same service, keeps its stdout and exit status, and prints one deprecation line naming its replacement to stderr.

#### Scenario: Scoped impact inspection
- **WHEN** a mapped public interface changes
- **THEN** the matching document requires review and unmapped changes remain visible

#### Scenario: The documentation group lists its commands
- **WHEN** a user runs `ai-dlc docs --help`
- **THEN** exactly `check`, `review`, `gate`, `read`, `search` and `init` are listed and no empty command group is registered

#### Scenario: Legacy command names keep working with a deprecation notice
- **WHEN** a caller runs a former `ai-dlc project docs-*` command
- **THEN** the same service runs with the same stdout and exit status, the name is absent from the command list in `ai-dlc project --help`, and one deprecation line naming the `ai-dlc docs` replacement is printed to stderr

#### Scenario: A review mode is given incomplete options
- **WHEN** `ai-dlc docs review` is run with a mode flag whose required options are missing, with two modes at once, or with a mode-specific option and no mode
- **THEN** the CLI reports a usage error and runs no service
