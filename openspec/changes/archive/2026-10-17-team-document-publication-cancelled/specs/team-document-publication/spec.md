## ADDED Requirements

### Requirement: DP-01 Separate private knowledge and publication
Team publication SHALL be an optional documents capability independent from private knowledge, and SHALL publish only explicitly selected eligible repository files.

#### Scenario: A project uses Confluence and Obsidian
- **WHEN** shared publication is configured alongside local knowledge
- **THEN** notes remain in the local vault and selecting Confluence does not upload or scan the vault for publication

#### Scenario: A source escapes the approved document root
- **WHEN** a selected path or symlink resolves into private notes or outside the approved repository roots
- **THEN** publication refuses before remote mutation

#### Scenario: Private notes inform a shared draft
- **WHEN** a user selects and reviews a separate eligible shared document derived from private working notes
- **THEN** publication includes only the reviewed document payload and does not traverse private source links or automatically include vault files

### Requirement: DP-02 Review exact content and destination
Publication preview SHALL expose exact source, conversion result, destination identity and expected remote version, and apply SHALL require that reviewed plan to remain current.

#### Scenario: The source changes after preview
- **WHEN** apply observes a different source digest
- **THEN** it requests a new preview without publishing changed content

### Requirement: DP-03 Preserve team edits
Publication SHALL refuse to replace an existing page whose identity or version differs from the reviewed target and SHALL not treat matching titles as ownership.

#### Scenario: A teammate edits the page
- **WHEN** the remote version changes between preview and apply
- **THEN** apply reports a conflict and preserves the teammate's content

### Requirement: DP-04 Faithful supported conversion
Conversion SHALL preserve the documented Markdown subset and report unsupported constructs before apply instead of silently dropping content.

#### Scenario: A document contains an unsupported embed
- **WHEN** preview encounters that construct
- **THEN** it identifies the source location and blocks publication until the content or supported scope is resolved

### Requirement: DP-05 Durable uncertain-operation recovery
Publication SHALL retain source-to-page provenance and reconcile uncertain mutations without duplicate creation or false success claims.

#### Scenario: Page creation times out
- **WHEN** the remote outcome is uncertain
- **THEN** retry searches the documented durable correlation or requires explicit target recovery, and does not blindly create another page

### Requirement: DP-06 No implicit workflow coupling
Work finish and private note operations SHALL retain existing behavior when publication is configured, and publication SHALL not be a new completion gate unless separately specified and selected.

#### Scenario: A tracked work item finishes
- **WHEN** its existing completion gates pass
- **THEN** no Confluence page is created or updated merely because the documents role is configured

### Requirement: DP-07 Selective shared-knowledge guidance
When Confluence and Obsidian are selected, generated harness guidance SHALL distinguish private working notes from shared team sources, direct agents to use relevant page links and reads on request, and SHALL NOT prescribe automatic site or vault mirroring.

#### Scenario: A user needs context from a team guide
- **WHEN** guidance is generated for the selected document and knowledge tools
- **THEN** it describes reading relevant pages without implicitly creating local copies, and saving a requested local summary with source URL, available version and retrieval date

#### Scenario: A user refreshes a saved summary
- **WHEN** generated guidance describes refreshing local derived context
- **THEN** it requires explicit refresh, preservation of personal annotations and honest stale or inaccessible-source reporting

#### Scenario: Native tools have broader permissions
- **WHEN** selected page or space guidance accompanies a native connection
- **THEN** setup distinguishes relevance guidance from enforced access controls and reports native-tool qualification separately from generated-instruction checks
