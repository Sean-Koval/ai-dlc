## MODIFIED Requirements

### Requirement: GT-03 Identity and uncertain recovery
Issue and project operations SHALL verify configured identity, refuse incomplete or ambiguous reconciliation, and preserve uncertainty across partial issue/project writes. A Project Done status SHALL NOT independently establish work completion or bypass finish gates. When an attachment returns an item identity that the membership readback does not yet show, the readback SHALL be retried within a bounded number of attempts with backoff without repeating the attachment request. Absence that persists past the bound, a different visible item identity and ambiguous membership SHALL remain terminal and uncertain.

#### Scenario: Project write partially fails
- **WHEN** an issue transition succeeds and the project status write fails
- **THEN** the operation is uncertain and reconciliation reports the actual remote state without inventing success

#### Scenario: New membership is not visible yet
- **WHEN** attachment returns an item identity and the first membership readback does not show that item
- **THEN** the readback is retried within the bound, succeeds with verified membership once the item appears, and no second attachment request is sent

#### Scenario: Membership never appears
- **WHEN** the attached item stays invisible past the retry bound
- **THEN** the attachment is reported uncertain rather than assumed from the mutation response

#### Scenario: A different item is visible
- **WHEN** the readback shows an item identity other than the one the attachment returned
- **THEN** the operation fails immediately without further retries
