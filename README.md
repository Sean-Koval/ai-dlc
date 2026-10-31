<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/banner-dark.svg">
  <img alt="ai-dlc: one pinned machine profile, one workflow for people and agents, a finish that needs merged evidence." src="docs/assets/brand/banner-light.svg" width="960" height="320">
</picture>

# ai-dlc

**Every developer's machine is set up differently, and every coding agent closes tickets on
its own idea of "done".** ai-dlc pins every machine to one profile and gives agents one workflow
in Claude Code or Codex. It closes a ticket only when the merged commit has a passing CI receipt.

Docs site: <https://sean-koval.github.io/ai-dlc/> · Part of the
[agent factory](https://sean-koval.github.io/agent-factory/) (Define / Run / Judge / Govern, and ai-dlc
as Setup).

> **Scope freeze (2026-10).** ai-dlc is a local workflow, machine-provisioning and
> work-lifecycle tool. Features outside the in-scope list in
> [ADR 0001](https://sean-koval.github.io/ai-dlc/decisions/0001-refocus-ai-dlc/) are frozen; bug fixes are welcome.
> `ai-dlc eval` moved to flightdeck.

## See it work

Enroll a machine from a pinned profile (preview, apply, status). Each recording opens on its
finished session, replays once and holds its last frame:

<picture>
  <source media="(max-width: 600px)" srcset="docs/assets/front/enroll-phone.svg" width="379" height="265">
  <img alt="machine enroll previews and applies a profile; machine status reports the pinned commit and one unbound credential" src="docs/assets/front/enroll.svg" width="691" height="435">
</picture>

Take one piece of work from a reviewed record to a closed ticket. GitHub and its CI are a
local stand-in ([`demo_provider.py`](docs/assets/front/demo_provider.py)) that speaks the
provider contract. The gates below check a real local merge and the receipt `project check`
wrote:

<picture>
  <source media="(max-width: 600px)" srcset="docs/assets/front/work-phone.svg" width="379" height="418">
  <img alt="work finish refuses until the PR is merged, then verifies the CI receipt and closes issue 42" src="docs/assets/front/work.svg" width="691" height="435">
</picture>

## What it looks like

The workflow plugin's skills, as Claude Code lists them, and the checks a project requires:

![Claude Code lists the ai-dlc-workflow plugin: eleven skills and three hooks](docs/assets/front/plugin-skills.svg)

<picture>
  <source media="(max-width: 600px)" srcset="docs/assets/front/project-check-phone.svg" width="379" height="435">
  <img alt="ai-dlc project check --required in the demo project: a clean tree and every required check passing" src="docs/assets/front/project-check.svg" width="691" height="418">
</picture>

## Where it sits

<picture>
  <source media="(prefers-color-scheme: light)" srcset="docs/assets/front/suite-light.svg">
  <img alt="ai-dlc on the developer machine, GitHub as tracker and CI, and the workflow plugin pinned by the team harness." src="docs/assets/front/suite-dark.svg">
</picture>

ai-dlc does not run agents in the cloud or judge harnesses. hangar renders and runs
sandboxes, flightdeck evaluates, and ai-dlc authors the one optional plugin they pin.
Read more in the [hangar docs](https://sean-koval.github.io/hangar/), the
[flightdeck docs](https://sean-koval.github.io/flightdeck/) and the
[example team harness](https://github.com/Sean-Koval/team-harness), which pins this plugin.

## Use cases

- **A new engineer is productive on day one.** They enroll their laptop from the team's
  profile at a reviewed tag. They get everyone's runtimes, Claude Code and Codex settings and
  named credentials, with their own paths and accounts. `machine status` shows
  what drifted later.
- **An agent cannot declare victory early.** A developer and their agent take an issue
  through `work start` and `work pr`; `work finish` refuses until the PR is merged into the
  target branch and that merge commit has a passing CI receipt, then closes the issue.
- **A team measures whether its workflow helps.** The maintainer publishes the workflow
  plugin into the team harness (`scripts/publish_workflow_plugin.py`), off in `stable` and on
  in `candidate`. flightdeck compares agent runs with and without it.

## Get started

Needs git and curl on macOS or Linux (native Windows is not supported yet). These commands
take a fresh machine to a project whose required checks pass:

```sh
git clone https://github.com/Sean-Koval/ai-dlc.git
cd ai-dlc
sh scripts/bootstrap.sh --source
export PATH="$HOME/.local/share/ai-dlc/bootstrap/bin:$PATH"
ai-dlc project init ~/demo-app
cd ~/demo-app
git init -q
ai-dlc project setup --root .
git add -A
git commit -qm "chore: initialize with ai-dlc"
ai-dlc project check --required
```

Bootstrap installs pinned uv, Python and mise; no preinstalled Python or Node is needed.
[Get started](https://sean-koval.github.io/ai-dlc/workflows/get-started/) covers existing work
repositories and contributing; [Configure a project](https://sean-koval.github.io/ai-dlc/workflows/configure/) covers GitHub and profiles.

Try the workflow plugin in Claude Code from this checkout. It is off by default, so enable it
for the session; adding `plugin list` after the same flags should report `Status: √ loaded`:

```sh
claude --plugin-dir plugins/ai-dlc-workflow --settings '{"enabledPlugins":{"ai-dlc-workflow@inline":true}}'
claude --plugin-dir plugins/ai-dlc-workflow --settings '{"enabledPlugins":{"ai-dlc-workflow@inline":true}}' plugin list
```

## Features

| Feature | What you get | Read more |
| --- | --- | --- |
| Machine enrollment | Versioned profiles pin runtimes, tools, agent clients and named credentials; each machine keeps its own paths and accounts | [Machine enrollment](https://sean-koval.github.io/ai-dlc/runbooks/machine-enrollment/) |
| Project scaffolding | `project init` / `project adopt` for generic, Python, Node or Rust repositories, with setup steps and required checks | [Get started](https://sean-koval.github.io/ai-dlc/workflows/get-started/) |
| Workflow plugin | Guidance, eleven skills and CLI-optional safety hooks for Claude Code, with a Codex form; off by default | [Workflow plugin](https://sean-koval.github.io/ai-dlc/workflows/workflow-plugin/) |
| Work lifecycle | Reviewed work records bind an issue, branch, specification and PR; `work finish` gates on the merge and its CI receipt | [Development workflow](https://sean-koval.github.io/ai-dlc/development-workflow/) |
| Receipts | `project check --required` runs the team's checks and writes a receipt bound to the commit | [Release verification](https://sean-koval.github.io/ai-dlc/release-verification/) |
| Documentation upkeep | Catalog, impact review, dispositions and a docs gate; decision records with knowledge-note frontmatter | [Project documentation](https://sean-koval.github.io/ai-dlc/design/project-documentation/) |
| Agent access | `ai-dlc mcp serve` exposes reviewed work, documentation and knowledge tools to agents | [Workflow tool map](https://sean-koval.github.io/ai-dlc/workflows/tool-map/) |
| Providers | GitHub Issues + Projects (default), Jira Cloud, OpenSpec, Obsidian | [Architecture](https://sean-koval.github.io/ai-dlc/architecture/) |

The front-page recordings and screens are generated by
[`docs/assets/front/build.py`](docs/assets/front/build.py), which runs the real CLI; CI
fails when they are stale.

## Read next

- [Get started](https://sean-koval.github.io/ai-dlc/workflows/get-started/): setup routes, then configuration, the plugin and example workflows.
- [Architecture](https://sean-koval.github.io/ai-dlc/architecture/): services, configuration layers and extension points.
- [Development workflow](https://sean-koval.github.io/ai-dlc/development-workflow/): discovery, greenfield, brownfield and design review.
- [Release verification](https://sean-koval.github.io/ai-dlc/release-verification/): platform and provider evidence and the remaining qualification gaps.
- [Docs home](https://sean-koval.github.io/ai-dlc/): every page the site publishes.
