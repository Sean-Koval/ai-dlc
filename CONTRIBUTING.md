# Contributing

Read [AGENTS.md](AGENTS.md) for repository boundaries and [the documentation
index](docs/index.md) for authoritative sources. ai-dlc ships Python; the
retired Rust implementation and its plans survive only in git history (before tag
`docs-prune-2026-10`).

ai-dlc is feature-frozen; [ADR 0001](docs/decisions/0001-refocus-ai-dlc.md) lists
what stays active. Changes outside the in-scope list are closed with a pointer;
bug fixes in frozen areas are welcome.

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

Portable skills live in `agents/` and project scaffolding in `project-templates/`.
Generated client copies are not independent sources of truth.

This repository does not commit rendered skill copies (`[agents] skills = []` in
`ai-dlc.toml`), so `.claude/skills/` and `.agents/skills/` stay empty here. Load the
team skills from the workflow plugin while working on ai-dlc. The plugin is off by default
(`defaultEnabled: false`), so enable it for the session:

```sh
claude --plugin-dir plugins/ai-dlc-workflow --settings '{"enabledPlugins":{"ai-dlc-workflow@inline":true}}'
```

To check it loaded, put the same flags before `plugin list` (after it, Claude Code
rejects `--plugin-dir`):

```sh
claude --plugin-dir plugins/ai-dlc-workflow --settings '{"enabledPlugins":{"ai-dlc-workflow@inline":true}}' plugin list
```

```text
  > ai-dlc-workflow@inline
    Status: √ loaded
```

Without `--settings` it reports `Status: × disabled` and no skills load.

Codex contributors read the same skills from `plugins/ai-dlc-workflow/skills/`.
Edit skills only under `agents/skills/`, then run
`python scripts/build_workflow_plugin.py` to refresh the plugin. Repository layout checks apply to ai-dlc itself; downstream projects
retain their chosen structure.

## Build the docs site

The site at <https://sean-koval.github.io/ai-dlc/> is built from `docs/` and
`mkdocs.yml` with Zensical, as `.github/workflows/docs.yml` does. To preview a
change locally:

```sh
pip install zensical==0.0.71
python scripts/docs_site_links.py --check   # links that would leave the site
zensical serve                              # or: zensical build --strict
```

CI runs the link check and `zensical build --strict`; a broken link or anchor fails
the build. `python scripts/docs_site_links.py --write` turns links to files the site
doesn't publish into GitHub URLs. The theme files in `docs/stylesheets/airframe*` and
the brand files in `docs/assets/brand/` are vendored from agent-factory; refresh them
with `sh scripts/sync-airframe.sh theme-vN` and `sh scripts/sync-brand.sh theme-vN`.

## Documentation placement

Current explanations belong in `docs/design/`, procedures in `docs/runbooks/` or
`docs/workflows/`, and verification records in `docs/verification/`. Formal plans
and requirements stay together in OpenSpec. Do not create a document solely to
report that a change completed; use git history for removed scratch reports.

[`docs/catalog.toml`](docs/catalog.toml) records the canonical documents with
their lifecycle and owner. It is an incremental inventory, not a claim that every
historical plan or verification record has been reviewed; run `ai-dlc docs check`
to inspect gaps, and review findings rather than deleting documents automatically.
[`docs/archive/`](docs/archive/README.md) is historical context whose old
instructions are not current guidance; the Rust plans, template research and dated
evidence captures pruned in October 2026 remain in git history at tag
`docs-prune-2026-10` (commit `fa867cc`), and the
[September 10 documentation baseline](docs/archive/verification/documentation-baseline.json)
keeps the pre-cleanup paths and hashes.

The documentation site publishes the pages listed in `mkdocs.yml`'s `nav`; it leaves
out `docs/archive/`, the dated verification records and reviews, and raw evidence,
all of which stay in the repository. Add a durable page to the `nav` beside its
catalog entry.

## Maintaining the workflow handbook

[docs/development-workflow.md](docs/development-workflow.md) and its guides form
one contract with the project template, the skills and the behavior they describe.

- Keep lifecycle stages and role names provider-neutral.
- Update [the tool map](docs/workflows/tool-map.md) when a configured provider,
  command, or skill changes.
- Update the greenfield or brownfield guide when initialization or adoption
  behavior changes.
- Update the design handoff when required design evidence changes.
- Store diagrams as Mermaid beside the text they explain. Exported images are
  optional views, never the editable source.
- Change the handbook, project template, relevant skills, and behavior in the
  same pull request when they form one contract.
- Use Git history for evolution; do not maintain a parallel changelog inside
  every guide.
