# Migration to v4

Inventory existing aliases, shell functions, PATH entries and installed ai-dlc/ai-dlc-cli binaries before selecting the Python entry point. Confirm both aliases resolve to the intended executable after installation. Remove obsolete Rust binaries only after migration fixtures prove supported command, configuration and work-record behavior. Keep a rollback copy until then.

Schema 4 separates portable project configuration from machine bindings. Review old provider selections and credentials; migrate secret values to environment variables. Select scm.repository explicitly. Machine-specific vault paths and account settings belong in machine configuration. Do not copy local journals as a substitute for remote state reconciliation.

For a personal profile such as `profiles/sean.toml`, create a separate private
profile repository and move the portable choices into its canonical
`ai-dlc-profile.toml`. Preview legacy enrollment, then repeat with `--apply`:

```sh
ai-dlc machine migrate SOURCE --profile-file profiles/sean.toml --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG
ai-dlc machine migrate SOURCE --profile-file profiles/sean.toml --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG --apply
```

The legacy preview can materialize an inactive cache, but does not change active
enrollment, client configuration, or package state. Its lock pins the resolved
commit when applied. After moving to the canonical filename, add
`profile_id = "legacy-development"` to `ai-dlc-profile.toml`, commit it, and
normal-enroll with that exact same stable ID:

```sh
ai-dlc machine enroll SOURCE --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG
ai-dlc machine enroll SOURCE --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG --apply
```

For an immutable advertised tag or ref, enroll that same ref on each additional
machine and expect `ai-dlc machine sync` to be idempotent. For an intentionally
movable advertised branch, `ai-dlc machine sync` previews later changes and
`ai-dlc machine sync --apply` activates a verified candidate. To move between
immutable tags, reenroll with the new ref. In every case, edit each machine
binding independently. Move every credential value into a password manager or
keychain that injects its configured environment-variable name; neither AI-DLC
files nor `.env` files are a credential store.

Initialize the specification provider (OpenSpec by default) using its supplied setup instructions, review existing formal specs, and link them to work. Configure the personal knowledge provider (Obsidian by default) with the intended vault and validate access. Preserve repository architecture, product rationale, decisions and runbooks as durable docs rather than copying them into the vault.

Adopting an existing project previews changes and reports path conflicts. Resolve user-authored docs/config deliberately before adoption; do not overwrite them. For upgrades, preserve Copier answers and the original accessible Git release. Bundled local-source adoption is a development fallback and does not promise cross-machine sync. Use the versioned repository template source for released projects.

Provider changes require `project rebind` planning. Existing work retains its old provider until explicitly mapped. An apply refuses affected work without replacement artifact mappings. TOML mappings use work IDs as tables and artifact kinds as keys, for example `[work-123]` with `tracker = "NEW-42"`. PR/branch references must both be mapped when both exist. Local completion claims alone do not prove completion, so the migration treats retained records conservatively. Review old and replacement artifacts before applying.

A reviewed Linear team/status change uses the same boundary. Save the non-secret
provider connection preview under `.ai-dlc/local`, prepare a mappings TOML entry
for every affected work ID listed by the refusal, then pass both files to `ai-dlc
project rebind tracker linear --connection-plan PLAN --mappings MAPPINGS
--no-plan`. For this connection-plan form, affected work means exactly records
whose effective tracker is Linear and whose tracker binding already exists. The
transaction freshly revalidates Linear membership, applies the exact saved
configuration digest, and computes replacement work bindings against that
configuration. Explicitly pinned alternate-provider records and unbound records
remain byte-for-byte unchanged. It does not create or mutate Linear issues and
never supplies artifact mappings automatically. Rebind behavior without a
connection plan remains the general provider migration described above.

No Jira, Figma, Windows, hosted orchestration, Obsidian create/attach, or
provider-discovery migration is provided by this release. Local CLI and MCP
execution remain the current control plane; hosted or cloud execution is a
later qualification target.
