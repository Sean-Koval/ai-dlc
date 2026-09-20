## Decisions

**One client first: Claude Code.** It is installed on the maintainer machine, has
a documented headless mode (`claude -p`) with `--output-format stream-json`, and
reports session id, turns, token usage and cost in its final event. Codex follows
only if the first report justifies a second client. Confirmed by the maintainer on
September 20, 2026.

**The driver is a contract, not a special case.** `driver.kind = "claude-code"`
joins `deterministic`. A driver receives the attempt, the goal and the limits,
and returns steps and usage. The stream is retained verbatim as evidence; a
malformed or truncated stream, or one without a final result event, makes the
attempt `incomplete`. Assistant text is never read for grading (EE-04 stands).

**Network: one destination, through a proxy.** EE-02's attempts have no network.
A real client must reach its model API. Each attempt joins a per-attempt internal
Docker network whose only other member is a proxy container that accepts CONNECT
to the hosts named in `profile.egress` (default `api.anthropic.com:443`) and
refuses everything else. The agent container has no route out except the proxy.
The proxy's log is retained; any refused destination is recorded and reported.
The proxy image is digest-pinned like every other image. Alternatives rejected:
host networking with firewall rules (not portable, needs root), and no
restriction (the agent could fetch a solution or a newer engine).

**Credential.** The profile names one environment variable
(`ANTHROPIC_API_KEY`); the value is read at run time, passed only to the agent
container's environment, never written to the plan, inputs or evidence, and
covered by the existing redaction. `eval plan` still reads no secret. A
subscription login is not supported: it needs an interactive browser and a
writable host credential store.

**Budgets are enforced, not just declared.** `max_turns` maps to the client's
turn limit. `max_spend_usd` and `max_tokens` are checked against the stream's
usage after each attempt; the run stops before starting an attempt that the
remaining budget cannot cover at the worst case seen so far. Recommended caps for
the first run: 20 turns, 30 minutes, USD 2 per attempt, USD 10 per run. Confirmed by the maintainer on September 20, 2026.

**Base image.** A Dockerfile under `evaluations/images/` builds from the pinned
Python image and adds Git and the pinned client version. `eval image` builds the
treatment image on top of it as today. Both arms therefore have the same client,
Git and Python; only the engine and its generated guidance differ.

**What the treatment arm gets.** The fixture project, after
`ai-dlc project adopt --apply` has run in the attempt's install stage, so the
agent finds the generated guidance, skills, hooks and MCP configuration the way a
user would. The goal prompt is identical in both arms and contains no commands or
skill text. Whether the agent uses the engine is the thing being measured.

**Git observer.** The collector already returns the project tree. The observer
reads the collected `.git` with the controller's Git, read-only, and records
commits, their order and changed paths. Assertion kinds: `commit-present`,
`path-committed`, `ordering` (work record committed before implementation).
Nothing else about process or MCP observation is added here.

**Attempts.** Three per arm by default, so the comparison can say more than
"one attempt". The claim stays descriptive: counts and ranges, no significance
test.

## Risks

- Model output varies; three attempts will often disagree. The report shows the
  spread instead of hiding it.
- The proxy is new attack surface inside the isolation boundary. It is a fixed,
  pinned image with a static allow-list and no credential.
- A real run costs money. Nothing runs on CI; every real run is started by hand.
