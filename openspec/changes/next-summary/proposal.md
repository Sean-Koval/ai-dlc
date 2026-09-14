# Replace the JSON context brief with a readable what-next summary

## Why
`ai-dlc context --brief` prints raw JSON for every work record. It answers "what is the state" for a machine, not "what should I do now" for a person or an agent starting a session. The `day-start` skill and the session-start hook both need the latter, and today the hook only tells the agent to run the JSON command. Issue #77 records the friction: sixty-odd records, no lifecycle state, no next action.

## What Changes
- A new offline `ai-dlc next` command SHALL derive each record's lifecycle state from its local artifacts alone: `unpublished` (no tracker artifact), `in progress` (tracker, no pull request), `awaiting merge, archive first` (pull request and an unarchived OpenSpec change) and `awaiting merge` (pull request and an archived change, or no specification required).
- The summary SHALL print a fixed plain-text shape with one line per active record, the required checks and the check command, and SHALL state that the tracker was not consulted. Records without a tracker are listed only with `--all`. `--json` SHALL return the same data with a `status` string.
- `ai-dlc context --brief` SHALL print that text; `ai-dlc context` without the flag is unchanged for machines.
- The session-start hook SHALL include the first ten lines of the summary in the context it returns.
- The tool map and the `day-start` skill SHALL point at `ai-dlc next`.

## Capabilities
### New Capabilities
- native-work-harnesses: NH-05 adds an offline next-step summary for people, agents and the session-start hook.

## Impact
`src/ai_dlc/work/` gains the summary; the CLI, MCP `work_context`, the session-start hook, the tool map, the `day-start` skill and their tests change. No tracker, SCM or network call is added; `work status` still consults the tracker and is unchanged.
