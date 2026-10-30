# Common provider connections

See how the common connection service discovers provider resources, saves a
reviewed plan and applies it, and what a new connection handler must supply.

The connection service in `src/ai_dlc/setup/connections.py` owns discovery
dispatch, named selection, saved plans and local configuration application. It
is separate from lifecycle provider registration. A custom lifecycle provider can
remain usable while guided setup reports that no connection handler is available.

`provider_definitions.py` is a trusted Python registry, not a project-configured
plugin loader. Each definition declares its kind, roles and selection keys.
New `ConnectionHandler` implementations supply read-only discovery and a pure
configuration-patch function; they do not receive an apply or saved-file callback.

The discovery contract requires schema 1, `complete=true`, a stable `account.id`
and `resources` for every selection key. Each resource has a nonempty stable `id`
and `name`. Handlers must return only non-secret metadata and redact transport
failures. Callbacks are trusted code; this interface is not a sandbox.

The service resolves an exact name or ID only when one discovered resource
matches, then stores canonical IDs. It validates the patch, protects bound work
for the definition's declared roles, and refuses TOML representations it cannot
preserve. Undeclared selections, duplicate legacy/generic selections and incomplete
resource sets fail before any plan is saved. `--select KEY=VALUE` is repeatable;
hyphens in keys normalize to underscores. Values are case-sensitive.

For example, Jira Cloud can use `--select project=OPS --select issue-type=Task
--select 'in-progress=In Progress' --select closed=Done` alongside its other
declared status selections. GitHub accepts its existing repository, Project and
status names through the same option, including `--select issues-only=true`.
Existing named flags remain accepted. To apply, pass only the provider, root,
`--plan-file` and `--apply`; selections come from that file. No default tracker
role is changed by connection setup.

The application API is one function, `connect_provider(root, name=..., environ=...)`.
Called with no selections it discovers; with selections and `plan_file` it saves
a plan; with `plan_file` and `apply=True` it applies that saved plan. Discovery retains
each builtin's existing preview behavior. In particular, GitHub's default Project
preview and journaled apply stay in its existing application service.

| Path | Saved plan and apply ownership |
| --- | --- |
| New declarative handler | Common service: exclusive confined plan creation, exact source bytes, effective runtime/work snapshots, complete rediscovery, locked authored-safe apply |
| GitHub existing selection | Existing codec/revalidation plus extracted common exact snapshot/render/save/apply primitives |
| GitHub default Project | Existing schema and Project journal orchestration, retaining its existing local helper calls |

Common exact plans bind provider kind/alias, account/resource identity, canonical
selections, patch and source/runtime/work digests. Apply recomputes the complete
plan and requires equality. Its local writer checks source/runtime/work again
under the project lock and immediately before replacement. Failed or replaced
stages are retained, and empty stage directories are deliberately not deleted
by mutable pathname. These are the inherited bounded same-user race protections,
not a claim of new crash-atomic or adversarial concurrency guarantees.

This child supplies shared write ownership for new handlers and useful extraction
for GitHub. GitHub's remote Project journal remains a compatibility boundary, so
the parent PT-02 extraction is not wholly complete. The Linear codec that also
stood outside the common service has been removed. This does not implement Jira
lifecycle support, native client login, Confluence or tenant qualification. See
the bounded
[specification](https://github.com/Sean-Koval/ai-dlc/blob/main/openspec/changes/archive/2026-09-07-provider-connection-service/specs/provider-connection-service/spec.md).
