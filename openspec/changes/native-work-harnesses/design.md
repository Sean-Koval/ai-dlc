## Design

Use existing project rendering and its owned-file/section manifest. Add a small
client layout table for supported client IDs/skill directories and dedicated
JSON MCP planning that keeps Claude's existing `mcp` ownership key compatible.
Antigravity has a separate ownership key. A dedicated owned rule contains the
actual guidance; it does not assume Claude's @import semantics. Its native
activation is checked explicitly in the client UI; no undocumented frontmatter
is fabricated. Existing default client selection is unchanged.

Remote definitions use documented client schemas. The public `agents.servers`
input remains unchanged. Antigravity env-name interpolation is deliberately
unsupported until its actual version contract is verified; OAuth URLs and stdio
commands without generated env overrides work. Secrets remain in native login or
an external process environment, never copied into project files. No broad
permissions, automatic client sign-in, new hook implementation or installer.

Official references inspected 2026-09-07:
- https://www.antigravity.google/docs/mcp
- https://www.antigravity.google/docs/skills
- https://www.antigravity.google/docs/rules-workflows
- https://code.claude.com/docs/en/mcp

These describe `.agents` workspace paths and distinct client transports. The
work laptop edition/version is still unknown; fixtures establish only emitted
configuration/ownership behavior. Record installed version, rule activation,
skill recognition and harmless MCP context/tool listing in an actual session
before declaring native qualification.
