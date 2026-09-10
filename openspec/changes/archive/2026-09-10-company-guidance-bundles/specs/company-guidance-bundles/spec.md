## ADDED Requirements

### Requirement: CG-01 Pinned skill references
Workflow bundles SHALL support declared Markdown skill references through a new compatible schema while retaining schema-1 behavior, pinned digests, safe paths, ownership and offline rendering guarantees.

#### Scenario: Pinned skill references
- **WHEN** an enrolled skill references a declared supporting page
- **THEN** all selected supported clients can resolve its local reference offline

### Requirement: CG-02 Applicable owned guidance
Company guidance SHALL identify its owner, source provenance, applicable SDK versions and review status. Tentative observations SHALL be distinct from approved rules; conflicting or incompatible selections SHALL produce actionable diagnostics.

#### Scenario: Applicable owned guidance
- **WHEN** a selected guidance version conflicts with declared SDK applicability
- **THEN** readiness surfaces the incompatibility instead of silently claiming readiness

### Requirement: CG-03 Deliberate knowledge promotion
Guidance SHALL define evidence-backed promotion from personal observation to reviewed company procedure. Existing company sources SHALL retain authority; selection SHALL not import unrelated company context or publish private notes.

#### Scenario: Deliberate knowledge promotion
- **WHEN** a project selects one company skill
- **THEN** only its declared supporting material is exposed and authored local edits survive updates
