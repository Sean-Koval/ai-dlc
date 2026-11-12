---
id: build-every-merge
type: decision
scope: team
status: accepted
date: 2026-09-15
owner: sean
sources:
  - {resource: https://example.invalid/pr/88}
links:
  - {type: supersedes, target: DEC-0003}
valid_from: 2026-09-15
title: Build on every merge
description: CI builds every merge to main; nightly-only builds are retired.
tags: [ci, builds]
verified:
  - {by: 'human:sean', at: 2026-09-15T17:00:00Z}
  - {by: 'process:ci-nightly', at: 2026-09-16T02:00:00Z}
stale_after: 2027-03-15T00:00:00Z
---
# Build on every merge
