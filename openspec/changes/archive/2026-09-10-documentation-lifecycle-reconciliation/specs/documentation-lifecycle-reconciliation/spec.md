## ADDED Requirements

### Requirement: DL-01 Honest delivery navigation
Roadmap and handoffs SHALL distinguish implemented, proposed, historical, cancelled and unverified scope using GitHub closure reasons and revision evidence.

#### Scenario: Honest delivery navigation
- **WHEN** a cancelled issue appears Done in a board
- **THEN** navigation retains cancelled status without claiming verification

### Requirement: DL-02 Canonical lifecycle cleanup
Delivered PR28 requirements SHALL be reconciled and archived using OpenSpec; canonical spec purposes SHALL describe their actual requirements. Historical Rust and decision rationale SHALL be retained.

#### Scenario: Canonical lifecycle cleanup
- **WHEN** the delivered linking change is archived
- **THEN** work references follow the archive and no second specification home is created

### Requirement: DL-03 Accounted documentation baseline
Every existing docs-check diagnostic SHALL be repaired or explicitly dispositioned with its path, reason and responsible role. No review date SHALL be inferred from file timestamps or test success.

#### Scenario: Accounted documentation baseline
- **WHEN** historical material remains outside active guidance
- **THEN** its disposition is discoverable without declaring the content current
