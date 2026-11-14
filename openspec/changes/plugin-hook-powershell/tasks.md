## 1. Hook

- [x] 1.1 Add `PowerShell` to the Claude PreToolUse matcher and rebuild the plugin (WP-05).
- [x] 1.2 Judge `PowerShell` in `ai-dlc hook pre-tool`; deny a shell call without a command string.
- [x] 1.3 Fail closed in the shim on an unreadable pre-tool payload, a missing command and an internal error; run the shim's check before delegating; resolve PowerShell case and backticks.
- [x] 1.4 Test PowerShell payloads in every mode, malformed payloads per event, a failing delegate and the generated shim; update the plugin README; run the required checks.
