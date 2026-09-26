## MODIFIED Requirements

### Requirement: FE-01 Optional frontend smoke

The node frontend capability SHALL add a Playwright smoke test and required
frontend-smoke check. Missing or empty BASE_URL SHALL fail nonzero with a remedy
to configure a running app, before invoking package/browser tools; it SHALL NOT
be reported as successful skipped smoke. Direct execution of the generated
Playwright smoke SHALL also fail for missing configuration rather than skip. The
check SHALL never install browsers or packages. A configured smoke SHALL visit
the app root, require a nonempty title and capture a screenshot under
.ai-dlc/local/design/smoke. Browser and dependency installation SHALL be explicit
setup. Existing authored manifests and checks SHALL retain their ownership.

#### Scenario: No server configured
- **WHEN** a generated frontend project runs frontend-smoke without a nonempty BASE_URL
- **THEN** smoke exits nonzero with an actionable configuration message
- **AND** it does not invoke package/browser tools or install anything

#### Scenario: Direct generated Playwright execution lacks configuration
- **WHEN** the generated Playwright smoke is invoked directly without a nonempty BASE_URL
- **THEN** it fails configuration validation rather than reporting a skipped success

#### Scenario: A local app is available
- **WHEN** BASE_URL names a running app with a nonempty title and browser dependencies are prepared
- **THEN** smoke visits it, writes a screenshot and succeeds without installing dependencies

#### Scenario: Configured smoke cannot verify the app
- **WHEN** the configured app is unreachable, its title assertion fails, or the prepared smoke runner fails
- **THEN** frontend-smoke returns failure rather than a successful skip

#### Scenario: Frontend composes with backend
- **WHEN** a node project selects frontend and backend in either order, optionally with SCM
- **THEN** both smoke and API contract checks, tool setup and generated assets remain present without creating provider roles for either pack or replacing an authored package manifest
