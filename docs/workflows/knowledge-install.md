# Install the team knowledge setup

How does a teammate who already uses Claude Code get the team harness and the
knowledge repository in one step, without losing their own setup?

## What it installs

`ai-dlc knowledge install` does four things, in order:

1. It checks that `claude`, `uv`, `gh` and `git` are on `PATH`. It names any that
   are missing and stops before writing anything.
2. It runs team-harness `scripts/install_local.py` for one harness channel in user
   scope. That installer adds the team's skills, hooks and deny rules to
   `~/.claude` and never overwrites a file it did not install.
3. It clones `KNOWLEDGE_REPO`, or reuses a clone of the same repository.
4. It adds a pre-commit hook that runs `ai-dlc knowledge check .`, but only when
   the clone has no pre-commit hook of its own and `core.hooksPath` is unset.
   Where `ai-dlc` is not on git's `PATH`, the hook warns and lets the commit through.

From a fresh machine, `sh scripts/bootstrap.sh --knowledge` runs the install and
the doctor after project setup.

## Settings

The install reads environment variables. On a terminal it asks for a required one
that is unset; with `--no-input`, or without a terminal, it stops and names it.

| Variable | Default | Meaning |
| --- | --- | --- |
| `KNOWLEDGE_REPO` | required | Git URL or local clone of the knowledge repository |
| `TEAM_HARNESS_REPO` | required | Git URL or local checkout of team-harness |
| `TEAM_HARNESS` | required | Harness directory under `harnesses/`, such as `work-default` |
| `TEAM_HARNESS_CHANNEL` | `stable` | Channel from `channels.yaml` |
| `KNOWLEDGE_CHECKOUT` | `~/knowledge/<name>` | Where the clone goes |

The values are written to `knowledge-install.toml` in the ai-dlc configuration
directory. Only names, paths and URLs are stored. A URL with a password, or a user
other than ssh's `git`, is refused; git's credential helper signs in instead.

A team-harness URL is cloned in full into the ai-dlc cache. The installer finds a
channel's pinned harness in git history, so a shallow clone would not work.

After it installs a harness, the harness installer checks that each guard hook
blocks, and fails if one may not. The install stops there. Remove the partial install
with `--uninstall`, and install again once team-harness promotes a release whose
guards block.

## Your own setup stays yours

Your `settings.json`, skills and hooks are kept byte for byte. The harness
installer merges its entries into `settings.json` and records what it added.
`ai-dlc knowledge install --uninstall` removes exactly those entries, the hook
while it is unchanged, and the stored settings. It never deletes the clone. A
harness you installed before running the install is left in place.

## Check the result

`ai-dlc knowledge doctor`, or `ai-dlc doctor --knowledge`, prints one line per
check: `pass`, `fail` or `skip`. It exits non-zero when any line fails. A failing
line names the variable or step to fix, never a value.

| Check | Passes when |
| --- | --- |
| `prerequisites` | The four tools are on `PATH` |
| `settings` | An install is recorded |
| `harness` | The manifest exists and `install_local.py --check` finds no drift; without the team-harness checkout, the line says drift was not checked |
| `tracker` | The `tracker` role fetches one item |
| `wiki` | The `wiki` role finds one page |
| `knowledge check` | The clone passes `ai-dlc knowledge check` |
| `inbox` | `inbox/` exists; the first item is listed |
| `versions` | The clone's `[format] version` matches ai-dlc's |

The tracker and wiki checks read `ai-dlc.toml` at `--root`, so run the doctor in
the work repository. Without that file, or without a provider for the role, the
line is `skip`. When a provider names `token_env` or `email_env`, an unset
variable fails the line by name.

The `versions` line prints the format version, the harness, channel, revision and
digest, the pinned model and the Claude Code version. Two installs of the same
channel print the same line, so teammates can compare them.

## Windows

The install and the doctor start the harness installer with the same Python that
runs ai-dlc, and Git for Windows runs the hook. CI runs their tests on Windows with a
stand-in installer only; the round trip with the real installer runs on Linux.

Windows is not supported yet. The bootstrap script is for macOS and Linux;
installing ai-dlc itself on Windows is open in
[#172](https://github.com/Sean-Koval/ai-dlc/issues/172).
