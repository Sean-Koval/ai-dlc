# Explain binding drift without changing identity

## Why
Historical fingerprints are intentionally preserved, but the refusal sounds like corruption and omits a usable active-work remedy. Issue #78 names `project rebind <id>`, which is not a supported command: project rebind migrates provider roles.

## What Changes
Explain the role's changed configuration, reviewed active-binding refresh, and historical `work validate --all`. Add a hint only when every single-record validation error is binding drift. Preserve fingerprints and all-record validation output.

## Capabilities
### Modified Capabilities
- spec-delivery-traceability: clarify binding drift remediation.

## Impact
Work resolution message, CLI hint, regression tests and both design-to-implementation guides.
