# AI-DLC documentation map

Start with [product direction](product-direction.md) for the framework's promise
and [roadmap](roadmap.md) for delivery dependencies. GitHub Issues and the linked
Project own current work status. This index links authoritative documents rather
than reproducing them.

| Question | Canonical entry point |
| --- | --- |
| What is the system? | [Architecture](architecture.md) and [delivery design](design/framework-delivery.md) |
| Why is it this way? | Decisions in the relevant [design documents](design/) and [formal change designs](../openspec/changes/) |
| What must it do? | [OpenSpec](../openspec/) owns formal specifications and change artifacts |
| How do we operate and verify it? | [README setup](../README.md), [release verification](release-verification.md) and [verification records](verification/) |
| Where are the details? | [Document ownership](design/project-documentation.md), [local/shared knowledge](design/local-and-shared-knowledge.md), and [contracts](../contracts/) |

[Catalog](catalog.toml) records selected canonical documents. It is an incremental
inventory, not a claim that every historical plan or verification record has been
reviewed. Run `ai-dlc project docs-check` to inspect gaps; findings require review,
not automatic deletion. Historical execution plans supply context but do not
supersede current product direction, formal requirements or tracker status.
