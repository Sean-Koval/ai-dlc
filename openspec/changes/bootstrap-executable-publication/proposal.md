## Why

Concurrent source bootstraps exposed a shared-tool startup stall. Independently,
the bootstrap copies directly over installed executables, changing bytes visible
to existing readers. This bounded #14 discovered-behavior child repairs publication;
it does not assert that in-place copying caused the observed macOS stall.

## What Changes

- Stage executable bytes and permissions on the installation filesystem before replacement.
- Isolate download temporary files per invocation and preserve failed staging occupants.
- Keep source and scaffold bootstrap copies identical and add real-script filesystem regressions.

## Capabilities

### New Capabilities
- `bootstrap-executable-publication`: Publish complete bootstrap executables without modifying previously installed objects.

### Modified Capabilities
None.

## Impact

Own scripts/bootstrap.sh, bootstrap/download.sh, matching project templates and
tests/test_bootstrap.py. No provider, harness, environment-locking or release work.
