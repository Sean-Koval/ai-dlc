# Contributing

Read [AGENTS.md](AGENTS.md) for repository boundaries and [the documentation
index](docs/index.md) for authoritative sources. AI-DLC currently ships Python;
the historical Rust implementation is retained for provenance and compatibility.

1. Start from the current roadmap and the linked GitHub issue. Read the relevant
   OpenSpec requirements before changing behavior. Keep formal change artifacts
   together in OpenSpec.
2. Prepare the checkout with `sh scripts/bootstrap.sh --source`. Use an isolated
   branch and add regression tests for observable changes.
3. Follow the [source map](docs/architecture.md#source-layout). Put durable docs
   in their existing home, update the catalog and record documentation impact.
4. Run `ai-dlc project check --required` and strict OpenSpec validation. Review
   generated changes and preserve authored content.
5. Describe the behavior, verification and remaining limits in the pull request.
   After merge and exact-revision CI, complete tracked work with `ai-dlc work finish`.

Portable skills live in `agents/`, current project scaffolding in
`project-templates/`, and supported legacy scaffold assets in `templates/`.
Generated client copies and embedded Rust snapshots are not independent sources
of truth. Repository layout checks apply to AI-DLC itself; downstream projects
retain their chosen structure.
