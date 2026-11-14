# Catch PowerShell's own deletes and git.exe in the workflow plugin hook

## Why

Since KAN-487 the plugin's PreToolUse hook sees `PowerShell` calls, but it judges
them with the POSIX rules. PowerShell's own deletes get through: `Remove-Item`
and its aliases `ri`, `del`, `erase`, `rd` and `rmdir`. Git named as `git.exe` or
by its full path also gets through, since only the word `git` matches; that holds
for `/usr/bin/git` in Bash too. Tracks
[KAN-493](https://seanmkoval.atlassian.net/browse/KAN-493).

## What Changes

- The classifier knows a program by its name alone: no directory and no `.exe`,
  `.cmd`, `.bat` or `.com`. So `/usr/bin/git`, `git.exe` and, in PowerShell,
  `C:\Program Files\Git\cmd\git.exe` are `git`, and `/bin/rm` is `rm`.
- In a `PowerShell` line, `Remove-Item` and its aliases `ri`, `rm`, `del`, `erase`,
  `rd` and `rmdir` count as `rm`, so any call is destructive, as a plain `rm` is in
  Bash. A backslash is read as a path separator there, never as an escape, and a
  backtick-escaped space stays inside its word. The commands inside a script block
  (`ForEach-Object { ... }`, `try { ... }`) and a dot-sourced program are judged too.
- git's global options (`-C <path>`, `-c <name>=<value>`, `--git-dir`,
  `--work-tree` and the like) are passed over to find the subcommand, so
  `git -C repo reset --hard` is destructive. A plain push in another repository
  stays unsupported, since that repository's push policy isn't readable here.
- The line `cmd /c` (or `/k`, `/r`) runs is judged as cmd.exe reads it:
  case-insensitively, with `^` escapes dropped, and with `del`, `erase`, `rd` and
  `rmdir` counted as `rm`.
- `ai-dlc hook pre-tool` and the shim share one entry point, `classify_shell`.

## Capabilities

### Modified Capabilities

- `workflow-plugin`: WP-05 judges PowerShell's own deletes and a program by its name.

## Impact

`Remove-Item one-file.txt` is now denied in PowerShell, as `rm one-file.txt` is in
Bash, and `cmd /c del x` is denied wherever it runs. Other wrappers (`sh -c`,
`powershell -command`, `Invoke-Expression`, `Start-Process`), a Windows path with
backslashes outside PowerShell, and Bash's own `{ ...; }` and `if ...; then`
bodies are still not inspected.
