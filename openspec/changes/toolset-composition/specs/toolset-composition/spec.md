## ADDED Requirements

### Requirement: TC-01 Definition-driven scaffold selection
Project adoption and initialization SHALL validate selected provider roles and supported agent clients through a pure plan, preserve omitted legacy defaults, and persist selected non-secret configuration in Copier answers. They SHALL NOT invent account bindings or execute service operations.

#### Scenario: A project selects a declared tracker and native clients
- **WHEN** adoption selects a declared tracker, Obsidian knowledge, Claude Code and Antigravity
- **THEN** preview and applied configuration reflect those selections independently of language preset, and repeat client options retain each selected client once

#### Scenario: A caller retains historical defaults
- **WHEN** provider and client options are omitted or a historical Copier answer file is updated
- **THEN** previous Linear and Claude Code/Codex defaults and finish gates remain intact

#### Scenario: Authored content conflicts during adoption or update
- **WHEN** a selected scaffold would conflict with authored content
- **THEN** conflict is reported and the destination bytes remain unchanged

#### Scenario: A Copier update retains or introduces an unsupported choice
- **WHEN** retained answers or staged update answers select an unregistered provider/client or a mismatched trusted provider default fragment
- **THEN** update refuses before destination writes while valid legacy and selected answers remain compatible

### Requirement: TC-02 Honest local knowledge and unavailable lifecycle readiness
Readiness SHALL inspect Obsidian's actual runtime vault directory without requiring its optional GUI, and SHALL distinguish an explicitly unavailable tracker lifecycle adapter from delivered guidance. Component catalog schema 1 SHALL remain unchanged.

#### Scenario: A vault exists in a headless environment
- **WHEN** paths.vault names an existing directory and the optional desktop viewer is unavailable
- **THEN** the note-storage requirement is ready, the viewer limitation is reported separately, and no live or write qualification is asserted

#### Scenario: The runtime vault is absent
- **WHEN** paths.vault is missing or does not name an existing directory, even if a provider-local vault setting exists
- **THEN** note-storage readiness is blocked with a configuration next action and no directory is created

#### Scenario: Plane guidance is selected without a lifecycle implementation
- **WHEN** a project selects Plane and its native instructions are delivered
- **THEN** readiness still explicitly blocks lifecycle operations without requiring Plane for projects selecting another tracker
