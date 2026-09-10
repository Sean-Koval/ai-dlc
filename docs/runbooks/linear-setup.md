# Linear connection setup

`ai-dlc provider connect linear --root PATH` reads the organization, every team,
and every workflow state visible to the project's configured `token_env`. With no
selection flags it prints that complete discovery and writes nothing. It never
chooses between duplicate team names or multiple `started` states.

For an authorized sandbox read-only walkthrough:

1. Confirm `PATH/ai-dlc.toml` selects the intended Linear credential environment
   variable and inject that variable into the current process. Do not put its value
   in the project, `.ai-dlc/local/`, or the command line.
2. Confirm the credential is restricted to the intended sandbox organization and
   that no apply or selection flags are present.
3. Run `ai-dlc provider connect linear --root PATH` and review the returned
   organization, team IDs, and all workflow-state IDs/types. This procedure makes
   GraphQL reads only; it does not create keys, change accounts, create projects or
   issues, or update the repository.
4. Record live evidence only when the actual authorized sandbox read completed.
   Fixture output proves behavior, not live access or qualification.

To prepare a change, pass all four explicit selection flags:
`--organization`, `--team`, `--in-progress`, and `--closed`. Add `--plan-file
.ai-dlc/local/linear-plan.json` to save the reviewed non-secret JSON plan. Apply
only that saved plan with `--plan-file ... --apply`; apply repeats read-only
discovery, revalidates every saved ID and type, and refuses source, plan, remote
membership, or work-binding drift.

Existing tracker-bound work requires an explicit connection rebind. Run the
selection preview with `--plan-file .ai-dlc/local/linear-plan.json`; the command
saves that non-secret plan but refuses the shared mapping change and lists every
affected work ID. This affected set contains only work whose effective tracker
is Linear and which already has a tracker binding. Create
`.ai-dlc/local/linear-rebind.toml` with one table for every listed ID and an
explicit replacement tracker reference:

```toml
[work-one]
tracker = "SAN-101"

[work-two]
tracker = "SAN-102"
```

Review the saved connection plan, every old and replacement tracker artifact,
and the fresh sandbox scope. Then apply both the mapping and work migration as
one transaction:

```sh
ai-dlc project rebind tracker linear --root PATH --connection-plan .ai-dlc/local/linear-plan.json --mappings .ai-dlc/local/linear-rebind.toml --no-plan
```

This command rejects incomplete mappings, a stale or tampered plan, changed
remote membership, a non-Linear effective adapter, or concurrent project edits
before changing shared files. It computes each replacement binding against the
new configuration. Work pinned to another tracker and work without an existing
Linear tracker binding are not migration inputs and their records remain
byte-for-byte unchanged. The process is explicit: provider onboarding never
invents tracker references or rebinds work automatically.
