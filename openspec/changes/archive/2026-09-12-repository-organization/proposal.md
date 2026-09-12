# Repository organization

## Why

Stale Rust instructions in CLAUDE.md conflict with the Python implementation.
Historical plans remain in root and tool-specific directories, and 49 Python
modules share one directory. PR35 records historical debt but does not relocate it.

## What Changes

Consolidate agent context in AGENTS.md; render plain Claude references without
removing authored context. Classify and relocate historical documents, repair
current links, remove repository-local Superpowers artifacts, group internal
Python modules by responsibility, and enforce the agreed layout in required checks.

## Impact

CLI commands, MCP tools, provider contracts and supported console entry points
remain stable. Internal Python imports move; tests and packaged paths must follow.
Historical Rust and legacy scaffold compatibility remain available. No remote
service mutation or deletion of active work is part of this cleanup.
