## MODIFIED Requirements

### Requirement: TR-04 Explained merged-revision specification gate
The specification gate SHALL continue to require a checkout that is exactly the pull request's merged revision with a clean specification tree. When it refuses, the blocked reason SHALL name the expected merged revision, the revision the checkout actually holds and the remedy. An unreadable checkout revision and a dirty specification tree SHALL be reported as distinct reasons. Canonical and generated delivery guidance SHALL describe finishing work after the target branch has moved past the merge.

#### Scenario: The target branch moved past the merge
- **WHEN** finish runs from a checkout that is not the merged revision
- **THEN** the blocked reason names both revisions and directs the user to a temporary detached checkout at the merged revision, and no tracker state changes

#### Scenario: The merged revision is checked out with dirty specification files
- **WHEN** the checkout is the merged revision but specification files are modified or untracked
- **THEN** the gate refuses with a dirty-tree reason naming that revision rather than a revision mismatch

#### Scenario: Guidance describes the procedure
- **WHEN** a person or agent reads canonical delivery guidance, or generated guidance for the applicable OpenSpec, SCM and tracker selection
- **THEN** it explains preparing a temporary detached checkout at the merge commit, finishing there and removing it afterwards

#### Scenario: An active change is reported before merge
- **WHEN** local work status or PR preparation sees an active OpenSpec change
- **THEN** it reports active change, archive before merge; status requires no network call

#### Scenario: The gate names the archive remedy
- **WHEN** required specification evidence still references an active change
- **THEN** finish names work archive on the delivery branch or a linked follow-up pull request without relaxing its gates

#### Scenario: Archive commits only its selected work
- **WHEN** work archive runs for a reviewed record and its own active change
- **THEN** the adapter archives and promotes it, the service repoints spec and a contained plan, and commits only affected specification files and the record

