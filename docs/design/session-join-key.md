# Session join key

This page is the one place the session join key's format is written down
([ADR 0002](../decisions/0002-jira-work-tracker-and-trace-correlation.md)).
Flightdeck, hangar and trace review read it to tie a trace to its ticket and its
ai-dlc work ID. ai-dlc still captures and exports no traces.

## Format

```text
aidlc1:<tracker>:<work>:<session>
```

| Part | Value | Empty when |
| --- | --- | --- |
| `aidlc1` | The format version. A new format gets a new prefix. | Never |
| `tracker` | The bare ticket key, such as `KAN-463`, or an issue number. | The session has no ticket |
| `work` | The ai-dlc work ID bound to the branch. | No work record is bound to the branch |
| `session` | The client's session ID, or a generated one. | The key was written outside a session |

Each non-empty part matches `[A-Za-z0-9._-]{1,100}`, so a key never needs
quoting. An empty part is an empty string between colons, never an error. For
example, `aidlc1::fix-typo:4f1c` is a session without a ticket.

## Where it comes from

Nobody types it. When an adopted repository starts a session, the workflow
plugin's session-start hook runs `ai-dlc hook session-start`. That derives the
key in this order:

1. The work record whose `artifacts.branch` is the current branch gives the work ID.
2. That record's `artifacts.tracker` gives the ticket. A browse or issue URL is
   reduced to its last path segment.
3. Without a ticket there, a branch that starts with a key, such as
   `KAN-463-session-join-key`, gives the ticket.
4. The hook payload's `session_id` gives the session. A missing or unsafe one is
   replaced with a random hex ID.

A key already in the environment is kept, so a key that hangar or a parent
session set is not replaced. Inside a hangar sandbox the plugin does not run
the CLI at all; hangar owns those fields
([KAN-320](https://seanmkoval.atlassian.net/browse/KAN-320)).

## Where it is written

| Place | Form |
| --- | --- |
| Session environment | `AI_DLC_SESSION_KEY`, plus `AI_DLC_TRACKER_KEY`, `AI_DLC_WORK_ID` and `AI_DLC_SESSION_ID` |
| Work record | One entry per session in the record's `sessions` list |
| Commits | A `Work-Session: <key>` trailer |
| Pull request body | One `Work-Session: <key>` line per session, written by `ai-dlc work pr` |

Claude Code gets the variables through the file named by `CLAUDE_ENV_FILE`, so
every later shell command sees them. Codex has no such file yet; it gets the
key in the session-start context only. The context also tells the agent to add
the trailer to each commit. ai-dlc installs no Git hook, so the trailer is an
instruction, not a guarantee.

## Reading it back

`ai-dlc work show <query>` takes a whole key, a session ID, a ticket key or a
work ID. It lists the matching work records with their sessions, so a session
ID resolves back to its ticket.

In Python, `ai_dlc.work.session_key.read_session_keys(text)` returns every key in
a commit message, PR body or trace note. `current_session_key()` reads the key
from the environment, and `SessionKey.parse` checks a single key.
