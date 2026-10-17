## MODIFIED Requirements

### Requirement: TC-01 Definition-driven scaffold selection
Project adoption and initialization SHALL validate selected provider roles and supported agent clients through a pure plan, select the GitHub Issues tracker and Claude Code/Codex clients when selections are omitted, and persist selected non-secret configuration in Copier answers. They SHALL NOT invent account bindings or execute service operations.

#### Scenario: A project selects a declared tracker and native clients
- **WHEN** adoption selects a declared tracker, Obsidian knowledge, Claude Code and Antigravity
- **THEN** preview and applied configuration reflect those selections independently of language preset, and repeat client options retain each selected client once

#### Scenario: Omitted selections and historical answers
- **WHEN** provider and client options are omitted
- **THEN** the GitHub Issues tracker, Claude Code/Codex clients and finish gates are selected, and no Linear provider or `LINEAR_API_KEY` reference is rendered
- **WHEN** a historical Copier answer file is updated
- **THEN** its recorded selections and finish gates remain intact

#### Scenario: Authored content conflicts during adoption or update
- **WHEN** a selected scaffold would conflict with authored content
- **THEN** conflict is reported and the destination bytes remain unchanged

#### Scenario: A Copier update retains or introduces an unsupported choice
- **WHEN** retained answers or staged update answers select an unregistered provider/client or a mismatched trusted provider default fragment
- **THEN** update refuses before destination writes while valid legacy and selected answers remain compatible

#### Scenario: Updated shared configuration violates scope or credential rules
- **WHEN** a staged Copier manifest introduces machine-only settings or literal credential fields
- **THEN** the standard project-layer validation refuses it before destination writes, while legitimate authored configuration and Copier conflicts retain their protections
