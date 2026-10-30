# Get started

Install ai-dlc, set up a project and run its required checks.

## From a fresh machine

Needs git and curl on macOS or Linux. These commands take a fresh machine to a
project whose required checks pass.

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

Bootstrap installs pinned uv, Python and mise, prepares the checkout and prints
the directories to add to `PATH`; no preinstalled Python or Node is needed. When
the global `ai-dlc` alias belongs to another checkout, use the checkout-specific
executable it prints.

`project init` copies the template only (`--preset generic|python|node|rust`,
`--agent-client claude-code|codex`). `project setup` runs the setup steps and
renders the agent configuration. The `generated` check fails until setup has
run; init's output and the failing check both name it.

## Add it to an existing repository

Adopt the repository with the preset that matches it and only the capability you
need. Every command previews first; repeat it with `--apply` to write.

1. Preview the adoption, inspect it, then repeat the exact command with `--apply`:
   ```sh
   ai-dlc project adopt --root /path/to/work-repository --preset generic \
     --capability agent-client --agent-client codex
   ```
2. Run the setup steps and render the agent configuration:
   ```sh
   ai-dlc project setup --root /path/to/work-repository
   ai-dlc agents render --root /path/to/work-repository --apply
   ```
3. Check local requirements: `ai-dlc project readiness --root /path/to/work-repository`
4. Commit the adopted files:
   ```sh
   git -C /path/to/work-repository add .
   git -C /path/to/work-repository commit -m "chore: adopt ai-dlc"
   ```
5. Run the required checks: `ai-dlc project check --root /path/to/work-repository --required`

Keep the repository's existing checks. Add at least one required check for its
own acceptance behavior; the generic management checks do not establish it.
Optional capabilities include `backend` contract checks and `frontend` browser
smoke tests. Checks bind receipts to the repository's `HEAD`.

`ai-dlc project onboard --root PATH --preset generic --agent-client codex` prints
the same route as a read-only JSON plan. Review each action's `argv`, effects and
`requires_review` before running it. A configured repository can run
`project onboard --root PATH` alone. Its `ai-dlc.toml` stays authoritative, and a
conflicting client or preset returns a blocked plan.

!!! note "The onboarding planner needs a source checkout"
    The published [v0.4.0](https://github.com/Sean-Koval/ai-dlc/releases/tag/v0.4.0)
    predates `project onboard`, though the package version is unchanged. To use
    the planner, bootstrap a team-reviewed commit or ref from a source checkout
    (`git checkout REVIEWED_COMMIT_OR_REF`, then `sh scripts/bootstrap.sh --source`).
    Projects made with the released engine carry its release manifest for their
    bootstrap and CI. Source-generated projects need a published
    `bootstrap/release.sh` first; see the
    [release guide](../runbooks/release-publication.md#install-from-a-release).

Enrollment is optional for a self-contained project. Select it only for a
portable profile and machine binding, with `--source`, `--ref`, `--profile-id`
and `--machine-id` together. [Work-computer setup](work-computer-setup.md) has
the full route; [machine enrollment](../runbooks/machine-enrollment.md) has its
separate preview/apply boundary.

## Contribute to the engine

Engine contributors use the source checkout itself as their project. After
`sh scripts/bootstrap.sh --source`, run the repository's full required checks
with the checkout-specific executable it printed:

```sh
AI_DLC=/absolute/path/printed/by/bootstrap/ai-dlc
"$AI_DLC" project check --required
"$AI_DLC" doctor
```

Do not use the engine checkout as the consumer work root or copy its tracker,
vault, provider or client choices into another project.

## Run checks while you work

During edits, run only the named commands relevant to the change:

```sh
ai-dlc project check --check generated
# Repeat --check to select more configured commands, in the requested order.
ai-dlc project check --check generated --check work-records
```

A focused run is local feedback. It cannot replace missing required outcomes in
completion evidence. After integrating the target branch, run
`ai-dlc project check --required` before merge.

Teams own the commands and required IDs in `ai-dlc.toml`. Keep their test tools
and add behavioral acceptance checks. New Python starters include a
standard-library test of their initial output and a syntax check; extend those
tests as the application grows.

!!! note "Platform limits"
    Native Windows is unsupported in this revision. The native storage core has
    source-level evidence, but the installer, PowerShell bootstrap, desktop clients
    and end-to-end onboarding remain open in
    [#172](https://github.com/Sean-Koval/ai-dlc/issues/172) and
    [#53](https://github.com/Sean-Koval/ai-dlc/issues/53). These instructions are
    for macOS and Linux hosts with a POSIX shell. WSL, containers and translated
    shell commands are not a Windows route.

## Next

- <span id="connect-tools-and-configure-the-project"></span><span id="carry-preferences-and-team-guidance-across-machines"></span>[Configure a project](configure.md):
  providers, settings and preferences across machines.
- <span id="workflow-plugin"></span>[Workflow plugin](workflow-plugin.md).
- <span id="example-workflows"></span><span id="take-a-ticket-through-delivery"></span><span id="keep-project-documents-useful"></span><span id="start-an-fde-engagement"></span>[Example workflows](examples.md):
  a ticket, document upkeep and an FDE engagement.
- <span id="how-the-tools-fit-together"></span><span id="feature-details"></span>[How the tools fit together](how-it-fits.md).
