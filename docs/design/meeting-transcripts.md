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

For each new transcript the pull writes two files into a local checkout:

- `inbox/transcripts/<slug>.txt`, the raw payload: one `[HH:MM:SS] Name: text`
  line per utterance.
- `inbox/transcripts/<slug>.md`, a Source record with `status: raw`. It holds the
  metadata, `sources: [{id, resource, hash}]` and `participants`.

The payload expires after 30 days. The Source record becomes permanent only when
extraction promotes it into a record directory. Participant emails are used for
routing and are never written.

The pull is idempotent by transcript id. A record anywhere in the checkout whose
`sources` cites `<provider>:<id>` means the transcript is already captured. Two
runs over one window therefore write each transcript once.

## Customer projects

A transcript routed to a project lands in `projects/<name>/inbox/transcripts/`.
A customer route adds `boundary: customer`, so the record never leaves its
project. A transcript that matches two projects is skipped, never guessed.

```toml
# knowledge.toml
[transcripts]
owner = "<record owner>"   # required
scope = "personal"         # unrouted transcripts: personal (default) or team

[[transcripts.projects]]
name = "alpha"
boundary = "customer"
titles = ["Alpha"]                 # substrings of the meeting title
participants = ["@alpha.example"]  # substrings of a name or email
```

The knowledge repository's retention job must also expire
`projects/*/inbox/`; today it reads only the top-level `inbox/` and `processed/`.

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
