# native-tool-composition Specification

## Purpose
Compose reviewed role bindings into native client connections with exact local apply, preserved manual configuration and explicit separation of declared and authenticated identity.
## Requirements
### Requirement: NT-01 Reviewed role and native connection composition
The agents CLI SHALL compose explicitly reviewed project bindings into existing agents.servers, deduplicating only exact alias, declared account and transport identity while preserving each selected role and its guidance.

#### Scenario: Two roles share an identical native binding
- **WHEN** reviewed bindings for two effective provider roles use the same alias, expected account and exact transport
- **THEN** one native server is planned and both roles retain their provider guidance

#### Scenario: One alias has conflicting identity
- **WHEN** requested bindings or an existing manual alias disagree on account, endpoint, command, arguments or environment names
- **THEN** composition refuses before configuration writes

### Requirement: NT-02 Exact local apply and manual compatibility
Composition SHALL reuse common safe saved-plan/application boundaries, reject changed project/input/runtime role/provider/account identity, and preserve unrequested manual server entries and authored source. Native rendering SHALL remain a separate explicit operation.

#### Scenario: A saved binding becomes stale
- **WHEN** project configuration, the reviewed binding artifact, or effective role/provider/account references differ from the saved plan
- **THEN** apply refuses without changing project configuration

#### Scenario: A reviewed configuration is applied
- **WHEN** an unchanged saved plan is applied
- **THEN** only the project configuration is updated, existing manual servers remain intact, and native rendering/authentication are reported pending

### Requirement: NT-03 Declared account expectations are not authenticated identity
Composition SHALL distinguish native account expectations from verified client authentication, preserve separate project configurations, and never infer that an alias changes an endpoint-shared OAuth login.

#### Scenario: Two projects declare different native accounts
- **WHEN** separate projects configure the same endpoint with different expected accounts
- **THEN** their local server definitions retain those distinct expectations and report actual native authentication unverified, including the endpoint-cache limitation

