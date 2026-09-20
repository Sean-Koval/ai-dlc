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

## Decisions made during task 3 (egress)

- The proxy is the existing conformance allow-listing proxy
  (`verification/test_proxy.py`), not a second one. It already connects the
  address it validated, so a second DNS answer cannot redirect it, and refuses
  non-global addresses. It gained one line of JSON per decision on stdout, and it
  no longer resolves names that are not on the list.
- Its source is passed to `python -c`; nothing is bind-mounted from the host.
- The profile gains `egress = {hosts, proxy_image}`. Port 443 only. `eval plan`
  refuses it with the deterministic driver and without a pinned proxy image.
- The agent container joins a per-attempt `--internal` network; the proxy is the
  only member that also has an external network. The stager, collector and grader
  keep `--network=none`.
- The proxy log is retained as `egress.jsonl`, hashed into the attempt's
  evidence, and summarised in an `egress` event. The report puts refused hosts in
  `metrics.egress_refused` and the timeline. A missing or malformed log makes the
  attempt `incomplete`; the collected tree is kept.
- Verified with real Docker on the maintainer machine: a direct connection to
  1.1.1.1:443 is blocked, CONNECT to `api.anthropic.com:443` returns 200, CONNECT
  to `pypi.org:443` returns 403 and is logged, and no container or network
  remains. That test needs the network and skips on hosted CI.
- Not covered: the agent can still send arbitrary data to a listed host. The
  allow-list limits destinations, not content.

## Risks

- Model output varies; three attempts will often disagree. The report shows the
  spread instead of hiding it.
- The proxy is new attack surface inside the isolation boundary. It is a fixed,
  pinned image with a static allow-list and no credential.
- A real run costs money. Nothing runs on CI; every real run is started by hand.
