# Meeting transcripts

How do meeting transcripts reach the knowledge inbox without anyone downloading
them?

Status: KAN-457, under [ADR 0004](../decisions/0004-knowledge-system-scope.md),
which made the `transcripts` role active. Fixture-tested; live qualification is
pending.

## The role

The `transcripts` role has two operations, listed in `contracts/README.md`.
`list_since` returns each transcript's id, title, start time and participants.
`fetch` returns the same with the text as speaker and timestamp segments.

| Provider | Reads | Transcript id |
| --- | --- | --- |
| `zoom` | Cloud recording transcripts (WebVTT) through the Zoom API | Meeting UUID |
| `google-meet` | Docs named `<meeting> - Transcript` in Drive, exported as text | Drive file id |

A transcript the token cannot read is skipped, and its id is logged. Swapping
the platform changes one provider and no skill.

## Pulling

```sh
ai-dlc knowledge pull-transcripts --since 2026-11-01 --into ~/src/knowledge
ai-dlc knowledge pull-transcripts --since 2026-11-01T09:00:00-05:00 --dry-run
```

MCP `knowledge_pull_transcripts` does the same, as a dry run by default. Without
`--into`, the pull writes into the knowledge role's local git clone.

For each new transcript the pull writes two files into the top-level `inbox/` of
a local knowledge checkout:

- `inbox/transcripts/<slug>.txt`, the raw payload: one `[HH:MM:SS] Name: text`
  line per utterance.
- `inbox/transcripts/<slug>.md`, a Source record with `status: raw`. It holds the
  metadata, `sources: [{id, resource, hash}]` and `participants`.

The payload expires after 30 days. The Source record becomes permanent only when
extraction promotes it into a record directory. Participant emails are used for
routing and are never written.

The pull is idempotent by transcript id. A record in the target checkout whose
`sources` cites `<provider>:<id>` means the transcript is already captured. Two
runs over one window therefore write each transcript once.

## Customer transcripts

Each customer has its own knowledge repository (KAN-475). A transcript that
matches a customer rule lands in that repository's top-level `inbox/`, with
`boundary: customer` and `project: <name>`. It never enters the team repository,
so the team repository's retention, numbering and index never see it.

The rules live in the team repository's `knowledge.toml`. A customer
repository's local path is a machine path, so an environment variable holds it.
If the variable is unset or names no knowledge checkout, the transcript is
skipped and logged, with no fallback to the team repository. A transcript that
matches two customers is skipped too.

```toml
# knowledge.toml of the team repository
[transcripts]
owner = "<record owner>"   # required: owner of the Source records
scope = "personal"         # team-repository transcripts: personal (default) or team

[[transcripts.customers]]
project = "alpha"
titles = ["Alpha"]                 # substrings of the meeting title
participants = ["@alpha.example"]  # substrings of a name or email
repo_env = "KNOWLEDGE_REPO_ALPHA"  # the default: KNOWLEDGE_REPO_<PROJECT>
```

## Credentials

Both providers follow the `jira-cloud` rules. Configuration names a variable,
never a value. The value is an OAuth access token from a keychain or the
environment, issued and renewed outside ai-dlc. Errors are fixed messages.

```toml
[roles]
transcripts = ["zoom", "meet"]   # one provider id, or several

[providers.zoom]
kind = "zoom"
auth_mode = "oauth_bearer"
token_env = "ZOOM_TOKEN"

[providers.meet]
kind = "google-meet"
auth_mode = "oauth_bearer"
token_env = "GOOGLE_MEET_TOKEN"
folder_id = "<Meet Recordings folder id>"   # optional
```

## Live qualification

Tests replay recorded API responses through fakes, with the network blocked.
They prove parsing, routing and idempotence, not account access. One provider
needs live qualification for 1.0, on a machine with real accounts (KAN-450):

- Zoom: a user-level OAuth app with `cloud_recording:read:list_user_recordings`,
  `cloud_recording:read:list_recording_files` and
  `meeting:read:list_past_participants`. Cloud recording and audio transcripts
  must be on for the account.
- Google Meet: `drive.meet.readonly`, or `drive.readonly` for transcripts that
  other organisers shared. Transcription must be on for the Workspace.
- Both: a transcript owned by someone else is skipped and logged, not an error.
