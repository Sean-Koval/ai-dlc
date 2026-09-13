# Legacy Claude Code scaffold

`ai-dlc scaffold --provider claude` copies the `.claude/` directory below into
the current project. It refuses to overwrite a file whose content differs, so
re-running it after local edits reports a conflict instead of clobbering them.
This is the compatibility scaffold kept from the retired Rust CLI; new projects
should use `ai-dlc project init` or `ai-dlc project adopt`, which render the
current harness configuration instead.

## What is copied

```
.claude/
├── settings.json                 # Claude Code settings: runs both checks when a turn ends
├── hooks/
│   ├── quality-gate.sh           # Format, lint, test and build checks for Rust, Python or Node
│   ├── security-check.sh         # Secret, permission, dependency and pattern scan
│   └── post-tool-notify.sh       # Optional desktop/Slack notification helper
└── workflows/
    ├── tdd/workflow.md           # Red-green-refactor guide
    └── feature-development/workflow.md  # Feature lifecycle guide
```

`settings.json` uses Claude Code's hook schema: the `Stop` event runs
`quality-gate.sh` and then `security-check.sh` from the project root. Both
scripts detect the project type from `Cargo.toml`, `pyproject.toml` or
`package.json` and skip tools that are not installed. `post-tool-notify.sh` is
not wired by default; it reads `TOOL_NAME`, `TOOL_STATUS` and `TOOL_DURATION`
from its arguments or environment and posts to Slack only when
`SLACK_WEBHOOK_URL` is set.

The workflow documents are plain guidance for a Claude Code session. They do
not define slash commands.

## Customising

Edit the copied files in your project. Add per-developer overrides in
`.claude/settings.local.json`, which Claude Code merges over `settings.json`
and which should stay out of version control.
