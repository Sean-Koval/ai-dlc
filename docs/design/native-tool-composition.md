# Reviewed native connections

`ai-dlc agents connect` composes explicitly reviewed role bindings into the
project's existing `agents.servers`. It provides an inspectable local setup path
for selected providers without installing tools, logging in or changing a service.
It reuses the common exclusive saved-plan and guarded configuration writer.

The scaffold selects providers and native clients. It does not invent a provider's
upstream MCP endpoint or authentication settings. This initial connection workflow
requires explicit transport definitions reviewed by the operator; it is not a
catalog of qualified upstream defaults. The existing manual `agents.servers`
format remains supported, including its legacy renderer semantics.

## Working local example

For a project whose selected tracker alias is `github-issues` and knowledge alias
is `obsidian`, create `docs/setup/native-bindings.toml`:

```toml
schema = 1

[[bindings]]
role = "tracker"
provider = "github-issues"
server = "ai-dlc"
account = "work"
command = "ai-dlc"
args = ["mcp", "serve"]

[[bindings]]
role = "knowledge"
provider = "obsidian"
server = "ai-dlc"
account = "work"
command = "ai-dlc"
args = ["mcp", "serve"]
```

Use the actual provider aliases selected in `ai-dlc.toml`. If an effective provider
has an `account` reference, including a machine override, the binding must match
that reference. If it has none, `work` is only your declared native expectation;
this operation does not set the provider's runtime account. This example shares
the installed AI-DLC MCP service between roles; it does not demonstrate access to
a live tracker or vault. Configure those providers and qualify them separately.

```sh
ai-dlc agents connect --root . --bindings docs/setup/native-bindings.toml \
  --save-plan .ai-dlc/local/native-plan.json
# Inspect the emitted roles, proposed server definitions and account notice.
ai-dlc agents connect --root . --apply-plan .ai-dlc/local/native-plan.json
ai-dlc agents render --root .
# Inspect the native rendering preview and resolve any authored conflicts.
ai-dlc agents render --root . --apply
```

Omit `--save-plan` for a read-only preview. Saved plans are exclusive, private local
files; a changed source, binding file, effective configuration or work binding
requires a fresh plan at a new path. No native file is checked against prospective
settings during config-only apply: the result explicitly reports rendering pending.
The separate renderer enforces its existing authored-file protections.

## Identity and preservation

One alias deduplicates only when declared account and transport match exactly:
URL, or command plus ordered arguments and environment variable names. Omitted
empty arguments/environment names equal empty lists. Both role selections and
provider guidance remain present. A conflicting alias refuses before writes,
including an old manual entry lacking the newly requested account identity.
Unrequested manual entries remain unchanged. Personal server defaults are never
copied into shared project configuration. Existing inline arrays (single or
multiline) and array tables retain their authored entries and comments; unfamiliar
representations that cannot be proven equivalent are refused.

Remote bindings accept an explicit HTTP(S) URL without user info, query or fragment.
Command bindings accept explicit arguments and environment variable names, never
an environment-value or secret-header object. Put credentials in the supported
external account/environment configuration; do not put secrets into command text.
Inputs stay in the repository and refuse symlinks. The component metadata schema
remains version 1; this separate reviewed input also has its own version 1.

An account is a declared expectation, not verified native authentication. Two
project configurations retain distinct expected accounts even for the same URL,
but native OAuth caches may be shared by endpoint. Changing an alias does not
switch the logged-in account. Inspect/authenticate the intended account in each
client before using tools. This workflow neither writes global client settings nor
qualifies Claude, Antigravity, a GUI, a provider API or an OAuth session.
