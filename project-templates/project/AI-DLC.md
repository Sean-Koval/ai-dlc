# Repository workflow

The repository owns durable architecture, product rationale, decisions, and runbooks. The specification role owns formal behavior specifications. The tracker owns priority and lifecycle status. Personal knowledge notes remain personal and link durable repository material.

Start with the [Development workflow](docs/development-workflow.md). It links the greenfield and brownfield paths, the design-to-implementation contract, and the current role-to-tool map.

Portable personal profiles belong in a separate private Git repository and are
enrolled at a pinned revision. Each machine maintains its own binding for local
paths, account selection, and credential environment-variable names. Keep
credential values in a password manager, keychain, or process environment;
never commit `.env` files or values to AI-DLC Git files. Local CLI and MCP
execution are current; hosted or cloud execution remains a later qualification
target. MCP exposes reviewed work, doctor, and selected knowledge services;
machine enrollment mutation remains CLI-only.

Select scm.repository and provider account/environment references before external operations. Every preset checks generated agent files. New-project initialization also creates a minimal language app and requires its syntax/compiler check; first setup creates its lockfile and later setup is locked. Adoption leaves existing application manifests/source untouched and requires existing language lockfiles. Add acceptance tests and further required check IDs as behavior develops.

This development template needs the AI-DLC release bootstrap artifacts before CI can run. The template includes reviewed scripts/bootstrap.sh and bootstrap prerequisite pins; supply bootstrap/release.sh and the corresponding locked artifact manifest from a published AI-DLC release. Verify the release integrity; do not download an unpinned latest script. No public release location is assumed.
