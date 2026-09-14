# Recover published release verification without replacing assets

## Why
Release run 34809544011 published v0.4.0 at cace021 but its Linux consumer jobs applied CI freshness rules to an uninitialized seed; macOS encountered a GitHub download error. Local first-use setup proves the published package works on the inspected host. Replacing intact assets would not fix the verification harness.

## What changes
Initialize both seed and generated demo before explicit CI checks. Add a manual existing-tag replay mode that skips package/publication and reads the unchanged release assets on three hosted runners. Preserve candidate dispatch and tag-push publication. Record actual success and failure boundaries in canonical release documentation.

## Impact
Release workflow and focused regressions; docs/release-verification.md and docs/runbooks/release-publication.md. No production freshness policy, package bytes or tag changes.
