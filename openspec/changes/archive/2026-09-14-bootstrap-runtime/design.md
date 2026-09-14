# Find the bootstrap runtime and repair the shell entry

## Context
`runtime_env` consults `shutil.which("mise")` only, so the process PATH decides whether any check can run even though the bootstrap installs `mise` at a known location that `workspace_diagnostics._bootstrap_bin` already computes. `setup.provision` carries its own copy of the same fallback. The owned shell section format is defined by `harness.agents.managed_section` with `toml=True` comment markers, written today only by `setup apply` for bash and zsh, and parsed back by `_configured_bin`.

## Goals / Non-Goals
Run checks whenever the bootstrap runtime exists; keep the receipt independent of how the runtime was found; give the user one copy-pasteable line per shell; write that line through one owned section without touching authored content. Do not install tools during checks, do not change which tools mise manages, do not modify the bootstrap installer, and do not make diagnostics mutate anything.

## Decisions
- One resolver. `ai_dlc.environment.bootstrap.bootstrap_bin(environ, home)` is the only place that derives the bootstrap bin directory (honouring `AI_DLC_BOOTSTRAP_HOME`, then `XDG_DATA_HOME`). Diagnostics, checks and provisioning import it; no package imports another package's private name.
- PATH of the check environment, not the process. `runtime_env` prepends the bootstrap bin to the `PATH` of the environment it returns when `mise` is absent from PATH but present there as an executable regular file. `subprocess` resolves the executable through that environment, so `run_command` needs no change. The process environment stays untouched and the receipt's `environment_digest` only hashes `.mise.toml` and the setup manifest, so it cannot differ between the two paths.
- One note per invocation. `check_project` resolves the runtime once before any check and is the only caller that prints the note; per-check `run_command` calls resolve silently. The note names the directory and the permanent remedy.
- Exact line per shell. `activation_line(shell, bin_dir, home)` renders `export PATH="$HOME/…:$PATH"` for bash and zsh and `set -gx PATH "$HOME/…" $PATH` for fish, using `$HOME` when the directory is under the home directory so the line is portable between machines. `configured_bin` accepts both forms and expands `$HOME`, so a section written with the portable line still matches the bootstrap bin during diagnostics.
- Fish joins bash and zsh as a supported shell with `~/.config/fish/config.fish`; other shells stay `unsupported-shell` and unverified.
- `workspace-init --shell` reuses the existing command rather than adding a parallel one; it previews by default and writes with `--apply`, like the other mutation commands. It refuses when the rc file is a symlink, unreadable or not a regular file, and when the owned section is modified or malformed. When a section from `setup apply` exists, only its PATH line is replaced so the brew and mise activation lines it owns survive.
- Rejected: exporting the bootstrap bin into the process `os.environ`, which would leak into unrelated subprocesses and hide the missing activation from the user. Rejected: having diagnostics write the section, which would break the read-only contract of `workspace-check`.

## Risks / Trade-offs
A stale `mise` in the bootstrap bin that PATH deliberately shadows would now be used when PATH has no `mise` at all; the stderr note makes the substitution visible. The activation-missing action changes wording; downstream guidance that quoted it is updated in the same change.

## Migration Plan
No configuration changes. Existing owned shell sections written by `setup apply` keep working; `workspace-init --shell` can repoint their PATH line.
