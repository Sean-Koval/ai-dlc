# Catch PowerShell's own deletes and git.exe in the workflow plugin hook

## Why

Since KAN-487 the plugin's PreToolUse hook sees `PowerShell` calls, but it judges
them with the POSIX rules. PowerShell's own deletes get through: `Remove-Item`
and its aliases `ri`, `del`, `erase`, `rd` and `rmdir`. Git named as `git.exe` or
by its full path also gets through, since only the word `git` matches; that holds
for `/usr/bin/git` in Bash too. Tracks
[KAN-493](https://seanmkoval.atlassian.net/browse/KAN-493).

## What Changes

- The classifier knows a program by its name alone: no directory and no `.exe`.
  So `/usr/bin/git`, `git.exe` and `C:\Program Files\Git\cmd\git.exe` are `git`,
  and `/bin/rm` is `rm`.
- In a `PowerShell` line, `Remove-Item` and its aliases `ri`, `rm`, `del`, `erase`,
  `rd` and `rmdir` count as `rm`, so any call is destructive, as a plain `rm` is in
  Bash. A backslash is read as a path separator there, never as an escape.
- `ai-dlc hook pre-tool` and the shim share one entry point, `classify_shell`.

## Capabilities

### Modified Capabilities

- `workflow-plugin`: WP-05 judges PowerShell's own deletes and a program by its name.

## Impact

`Remove-Item one-file.txt` is now denied in PowerShell, as `rm one-file.txt` is in
Bash. Wrappers (`cmd /c`, `Invoke-Expression`, `Start-Process`) and `git -C dir`
are still not inspected.
