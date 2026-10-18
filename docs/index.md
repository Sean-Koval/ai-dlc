<div class="af-hero" markdown>

<span class="af-eyebrow">Agent factory · Define plane</span>

# One pinned setup, one workflow, and a finish that needs merged evidence

<p class="af-lede">Every developer's machine is set up differently, and every coding agent closes tickets on its own idea of "done". AI-DLC gives a team one pinned machine profile, one workflow its agents follow in Claude Code or Codex, and a <code>work finish</code> that closes a ticket only when the merged commit has a passing CI receipt.</p>

[Get started](workflows/get-started.md){ .md-button .md-button--primary } [Suite overview](https://sean-koval.github.io/agent-factory/){ .md-button }

</div>

## See it work

Enroll a machine from a pinned profile (preview, apply, status):

![A terminal session: ai-dlc machine enroll previews the example profile's modules and credentials, applies it to a machine binding, and machine status reports the pinned profile commit and one unbound credential](assets/front/enroll.svg)

Take one piece of work from a reviewed record to a closed ticket. GitHub is played by a
local stand-in ([`demo_provider.py`](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/assets/front/demo_provider.py))
that speaks the provider contract, so the gates check a real local merge and the receipt
`project check` wrote:

![A terminal session: work new creates a record, a person marks it reviewed, work publish opens issue 42, work start creates the branch, work pr opens pull request 43, the branch merges, project check passes and writes a receipt, and work finish verifies the merge and CI receipt and closes the issue](assets/front/work.svg)

## What it looks like

The workflow plugin's skills, as Claude Code lists them, and the checks a project requires:

![Claude Code plugin details for ai-dlc-workflow: eleven skills and three hooks](assets/front/plugin-skills.svg)

![ai-dlc project check --required in the demo project: the required checks, a clean tree, and each check passing with exit code 0](assets/front/project-check.svg)

## Where it sits

--8<-- "docs/assets/front/suite.svg"

AI-DLC does not run agents in the cloud or judge harnesses: hangar renders and runs
sandboxes, flightdeck evaluates, and AI-DLC authors the one optional plugin they pin.
Read more in the [hangar docs](https://sean-koval.github.io/hangar/), the
[flightdeck docs](https://sean-koval.github.io/flightdeck/) and agent-factory's
[example team harness](https://github.com/Sean-Koval/agent-factory/blob/main/examples/team-harness/README.md),
which pins this plugin ([how to pin it](workflows/workflow-plugin-harness.md)).

## Use cases

- **A new engineer is productive on day one.** They enroll their laptop from the team's
  profile at a reviewed tag: the same runtimes, Claude Code and Codex settings and named
  credentials as everyone else, with their own paths and accounts. `machine status` shows
  what drifted later.
- **An agent cannot declare victory early.** A developer and their agent take an issue
  through `work start` and `work pr`; `work finish` refuses until the PR is merged into the
  target branch and that merge commit has a passing CI receipt, then closes the issue.
- **A team measures whether its workflow helps.** The maintainer publishes the workflow
  plugin into the team harness, off in `stable` and on in `candidate`, and flightdeck
  compares agent runs with and without it.

## Quickstart

Needs git and curl on macOS or Linux (native Windows is not supported yet). Five commands,
from a fresh machine to a project whose required checks pass:

```sh
git clone https://github.com/Sean-Koval/ai-dlc.git && cd ai-dlc
sh scripts/bootstrap.sh --source
export PATH="$HOME/.local/share/ai-dlc/bootstrap/bin:$PATH"
ai-dlc project init ~/demo-app && cd ~/demo-app && git init -q && ai-dlc project setup --root .
git add -A && git commit -qm "chore: initialize with ai-dlc" && ai-dlc project check --required
```

[Get started](workflows/get-started.md) covers existing work repositories, GitHub, profiles and
contributing to the engine.

## Features

| Feature | What you get | Read more |
| --- | --- | --- |
| Machine enrollment | Versioned profiles pin runtimes, tools, agent clients and named credentials; each machine keeps its own paths and accounts | [Machine enrollment](runbooks/machine-enrollment.md) |
| Project scaffolding | `project init` / `project adopt` for generic, Python, Node or Rust repositories, with setup steps and required checks | [Get started](workflows/get-started.md) |
| Workflow plugin | Guidance, ten team skills and CLI-optional safety hooks for Claude Code, with a Codex form; off by default | [Workflow plugin](workflows/workflow-plugin.md) |
| Work lifecycle | Reviewed work records bind an issue, branch, specification and PR; `work finish` gates on the merge and its CI receipt | [Development workflow](development-workflow.md) |
| Receipts | `project check --required` runs the team's checks and writes a receipt bound to the commit | [Release verification](release-verification.md) |
| Documentation upkeep | Catalog, impact review, dispositions and a docs gate; decision records with knowledge-note frontmatter | [Project documentation](design/project-documentation.md) |
| Agent access | `ai-dlc mcp serve` exposes reviewed work, documentation and knowledge tools to agents | [Workflow tool map](workflows/tool-map.md) |
| Providers | GitHub Issues + Projects (default), Jira Cloud, OpenSpec, Obsidian | [Architecture](architecture.md) |

The [documentation map](design/documentation-map.md) lists every canonical document.
