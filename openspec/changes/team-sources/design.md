# Team source design

The reviewed GitHub issue acceptance defines scope. Source subscriptions live only in personal schema 4 profiles. Machine `roles = ["developer"]` selects a person's team roles without replacing provider-role configuration. Source-level roles and tags add selection subscriptions; unannotated items apply to everyone, otherwise an item needs any matching role or tag.

Enrollment resolves every source ref using the existing safe Git transport boundary, validates the complete tree before selection, and caches only bounded regular UTF-8 files under a content digest. Lock entries contain subscription metadata, exact commit and digest. Rendering reads and verifies this cache offline. Sync resolves all candidates and preserves the existing lock until explicit apply and successful reconciliation. Session notices use bounded ls-remote only, never checkout, cache activation or rendering.

Native manifest.toml uses schema=1 and [[items]] with kind, name, path, roles and tags. Skills use skills/<name>/SKILL.md; rules use rules/<name>.md; MCP items reference mcp/servers.toml and supported hook items reference hooks/hooks.toml. MCP documents declare [[servers]] with id and command; arguments may contain non-secret command arguments. Hook declarations name existing AI-DLC features, never shell snippets.

A teamai adapter reads flat skills, rules, culture.md and the documented servers list in mcp/mcp.yaml. Filtering reads teamai.yaml metadata and Markdown frontmatter. Namespaced roles use manifest/roles.yaml when available. Hooks, agents and docs are ignored with notices after whole-tree safety validation. env/ is refused in both layouts per issue acceptance. Teamai is a source format, not a runtime dependency.

Render merges only enrolled source content into existing project-owned outputs, leaving unrelated personal settings out of shared project configuration. It rejects shipped/bundle/local/source skill collisions and MCP names, uses existing render ownership and transaction machinery, and removes previously owned source skills when deselected. All invalid cache/source checks occur before writes.

Canonical documentation is docs/runbooks/machine-enrollment.md and docs/product-direction.md. No new durable guide is required. Tests use local Git repositories only; external account qualification is outside this change.
