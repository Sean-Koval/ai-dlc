## REMOVED Requirements

### Requirement: DI-02 Revision-bound dispositions
**Reason**: Exact-base binding at one shared path makes concurrent branches conflict and forces evidence to be recorded again whenever the target branch moves (#146). Its scenarios "Target branch moves after disposition" and "Comparison base missing from the checkout" describe behavior that is withdrawn; "Revision-bound dispositions" and both work-record scenarios continue under the replacement.
**Migration**: Replaced by "DI-02 Content-bound dispositions" below. Schema 1 evidence keeps passing for one release.

## ADDED Requirements

### Requirement: DI-02 Content-bound dispositions
Documentation dispositions SHALL identify updated, reviewed-no-change or justified no-impact outcomes, each with a reason and reviewer, and SHALL bind each decision to the content of its target and of the sources mapped to that target, including that document's catalog entry. Evidence SHALL be stored per work item under `.ai-dlc/documentation/evidence/` so that concurrent branches do not write a shared path. Work records under `.ai-dlc/work/` SHALL be excluded from changed files, unmapped files and bound content unless a catalog mapping explicitly targets those paths; the work-records check validates their delivery state. The gate SHALL resolve its comparison independently of the evidence, SHALL compute changed files from the merge base of that comparison and `HEAD`, and SHALL require every impacted document and unmapped changed file to have a decision whose bound content equals current content. Missing decisions and stale decisions SHALL be reported separately, and a stale report SHALL name the paths whose content differs. Movement of the target branch that changes no bound content SHALL NOT invalidate a decision. Recording SHALL keep decisions that remain valid, SHALL refuse decisions for targets that are not required, and SHALL report kept, added, replaced and dropped targets. Schema 1 evidence at `.ai-dlc/documentation/current.json` SHALL keep passing under its recorded-base rules for one release when no per-work evidence exists.

#### Scenario: Bound content changes after disposition
- **WHEN** a target or one of its mapped sources changes after its decision is recorded
- **THEN** the gate reports that decision as stale and names the changed paths rather than accepting the earlier review

#### Scenario: Disjoint branches merge in either order
- **WHEN** two branches with disjoint changes each hold valid evidence and one merges before the other
- **THEN** the second branch updates from the target without a Git conflict in evidence storage, and its gate passes with no decision recorded again

#### Scenario: Target branch changes bound content
- **WHEN** the branch is updated from a target branch that changed a source bound by one of its decisions
- **THEN** the gate reports that decision as stale, names the source, and leaves the branch's other decisions valid

#### Scenario: Branch behind its target
- **WHEN** the comparison commit is not contained in `HEAD`
- **THEN** changed files are computed from the merge base, so target-branch changes the branch lacks are not reported as the branch's changes

#### Scenario: Push run on the target branch
- **WHEN** the gate runs on a merge commit with the replaced commit as its comparison
- **THEN** it requires valid decisions for what the merge introduced, and fails if conflict resolution altered bound content

#### Scenario: Catalog entry changes
- **WHEN** a document's catalog mapping changes after its decision while unrelated catalog entries also change
- **THEN** only that document's decision is stale

#### Scenario: Incremental recording
- **WHEN** new decisions are recorded for a work item whose evidence already holds decisions that remain valid
- **THEN** the valid decisions are kept, the new ones are added, decisions for targets no longer required are dropped, and the result lists each group

#### Scenario: A work record changes after dispositions are recorded
- **WHEN** a work record without an explicit catalog mapping changes after dispositions are recorded
- **THEN** the recorded documentation evidence still passes the gate

#### Scenario: A work record has an explicit catalog mapping
- **WHEN** an explicitly mapped work record changes
- **THEN** its mapped document requires review and its content remains bound to evidence

#### Scenario: Legacy evidence
- **WHEN** a project holds only schema 1 `current.json`
- **THEN** the gate applies the recorded-base rules, and the next recording writes per-work evidence and reports that `current.json` can be deleted
