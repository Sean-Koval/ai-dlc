# Portable profile and machine enrollment

Keep a personal `ai-dlc-profile.toml` in a separate private Git repository and
pin the revision enrolled on each machine. The profile owns portable modules,
logical credential requirements, and agent preferences; the project repository
owns shared policy and durable docs. Each machine independently owns its
binding, including paths, account selection, and environment-variable names.
Credential values belong only to a password manager, keychain, or process
environment. Generated Codex and Claude client files remain owned by their
client configuration, which AI-DLC updates through its ownership rules.

Use `ai-dlc machine status`, `plan`, `apply`, `sync`, and `doctor` to inspect,
preview, reconcile, update, and diagnose local enrollment. Local CLI and MCP
execution are the current control plane; hosted or cloud execution is a later
qualification target. Obsidian portals link an explicitly selected existing vault. Provider discovery
and onboarding use the selected adapter; offline readiness is not live qualification.

Use `ai-dlc project readiness --root PATH` to inspect the selected component
requirements offline. Its JSON separates tool availability, provider configuration,
credential presence, harness guidance, and provider health, with a next action for
each gap. Exit 0 means all required offline checks are ready; missing, blocked, or
unverified required checks return 1. Tools are located on the current environment's
PATH without execution. Credentials are checked only in that environment; secret
files are never loaded. Provider health stays informational and unverified, and
`qualification` is always `not-assessed`.

When `ai-dlc` is missing, reports an unexpected version, or works only in new
terminals, run `ai-dlc project workspace-check --root PATH`. It separates the
executable PATH selects from the AI-DLC-owned shell activation. If no `ai-dlc` is on
PATH, run the same check through the bootstrap's published alias by its full path,
by default `~/.local/share/ai-dlc/bootstrap/bin/ai-dlc` on Unix. Native Windows
uses the executable and activation procedure below. On Unix, `configured-for-next-shell`
needs only a new terminal or sourcing the shell file. Missing activation includes a
copy-pasteable PATH command for bash, zsh or fish. Preview permanent repair with
`ai-dlc project workspace-init --shell`; add `--apply` to write only the owned
section. Authored content and other owned lines are preserved; symlinked,
unreadable, non-regular files and edited owned sections are refused.
When mise is missing from PATH, project checks use the executable in the bootstrap
bin directory and emit one stderr note. Checks never install tools, and the
receipt's environment digest is independent of this fallback. When neither
location supplies mise, the command refuses before running checks or writing a
receipt. Rerun the bootstrap if its bin directory is absent.

The shared `ai-dlc` and `ai-dlc-cli` aliases are one machine-wide selection. Source
bootstrap prepares a separate environment per checkout and leaves an existing
working alias alone, so bootstrapping a linked worktree no longer changes the
`ai-dlc` other shells use; it publishes the aliases only with `--publish-aliases`
(`-PublishAliases` in PowerShell)
or when no working alias exists. Bootstrap output names the checkout the alias runs
and the executable for the current checkout. When the alias belongs to another
checkout, `project workspace-check` reports that checkout under activation.
Missing custom Markdown instructions produce a component-specific guidance gap
and a restoration action while independent checks continue. Manifest digest,
schema, path, and symlink violations still block catalog inspection.

`ai-dlc agents render --apply --root PATH` delivers the project-owned provider/tool
index in `AGENTS.md`, which Claude Code receives through its managed `CLAUDE.md`
import. Packaged instructions are owned copies in `.ai-dlc/providers/`; custom
component instructions remain linked project files. Edited or authored copies
are preserved through the existing conflict rules. A provider selected only in a
personal profile can have a missing-delivery gap: declare the intended shared
provider in `ai-dlc.toml` before rendering. Rendering does not promote private
configuration automatically. Missing component metadata is reported explicitly;
the index does not establish new provider or client support.
Rendering refuses any managed removal that would leave selected instructions
with a dangling link, including deselected skills in either client directory.
Move those instructions to a project-owned path and update the manifest first.

Setup plan/apply with `--root` adds selected project component requirements to
machine provisioning. Global MCP settings continue to use the personal profile
and machine configuration; project server lists remain scoped to the project.

Root and machine doctor retain their enrollment and readiness decisions and add
these offline diagnostics under `project_readiness`. Their existing explicit
provider-health inspection remains separate, as do work finish and release gates.

Preview a private profile enrollment can materialize an inactive cache, but it
does not change active enrollment, client configuration, or package state.
Repeat the same command with `--apply` to activate it:

```sh
ai-dlc machine enroll SOURCE --profile-id example-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG
ai-dlc machine enroll SOURCE --profile-id example-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG --apply
```

The lock always records the exact resolved commit. An immutable advertised tag
or ref gives cross-machine reproducibility, and `ai-dlc machine sync` is
idempotent for it. An intentionally movable advertised branch instead enables
`ai-dlc machine sync` to preview a candidate and `ai-dlc machine sync --apply`
to activate it after validation and reconciliation. To move from one immutable
tag to another, reenroll with the new ref. Enroll a second machine with the
same advertised ref under the selected policy and a different machine ID; its
local binding remains independent.

## Native Windows setup and activation

The native lane targets Windows x64, local NTFS, and 64-bit Windows PowerShell
5.1. From a reviewed AI-DLC source checkout, preview
`.\scripts\bootstrap.ps1 -Source -Root $PWD.Path -Plan`, then omit `-Plan` to prepare
that checkout. Native setup needs neither WSL nor preinstalled Python or Node.
The original published v0.4.0 assets cannot run this lane; see
[release compatibility](release-publication.md#native-windows-assets-and-compatibility).

Bootstrap defaults to `ai-dlc/bootstrap` under Windows' Local Application Data
known folder. `AI_DLC_BOOTSTRAP_HOME` explicitly selects a different local root;
it is not a shared project setting. Bootstrap prints the direct environment
`Scripts/ai-dlc.exe` path and PATH directories. The shared bin contains copied
`ai-dlc.exe` and `ai-dlc-cli.exe` launchers, with selection metadata bound to their
bytes and source/release identity. Source environments are separate from release
environments; rerunning an unchanged source selection can reuse its prepared
environment. A source bootstrap preserves an existing working shared selection
unless `-PublishAliases` is explicit. Private runtime directories and project
roots reject reparse points; use a regular local path when this guard refuses.

For persistent activation, choose the actual profile of the PowerShell host you
intend to use. In that host, pass its absolute `$PROFILE` path explicitly:

```powershell
ai-dlc project workspace-init --shell --powershell-profile $PROFILE
# Inspect the proposed owned section before applying it.
ai-dlc project workspace-init --shell --powershell-profile $PROFILE --apply
```

This updates only AI-DLC's owned section and preserves authored profile bytes,
including supported UTF-8/UTF-16 encodings. An edited owned section, reparse path,
signed or download-marked (`Zone.Identifier`) profile, or disallowed/unknown
execution policy blocks the edit. The
command neither bypasses policy nor elevates or changes machine PATH. When a
profile cannot be used, invoke the printed executable directly with PowerShell's
call operator, for example `& 'C:\path printed by bootstrap\Scripts\ai-dlc.exe' --version`.
After applying activation, open a new terminal and inspect `Get-Command ai-dlc`
and `ai-dlc --version`; run `ai-dlc project workspace-check --root PATH` to inspect
PATH selection and launcher provenance. Native workspace diagnostics report the
profile as unselected rather than guessing which PowerShell host profile you use.

Setup planning reports native requirements individually. Existing Git and GitHub
CLI installations are observed and reused when they meet the minimum versions.
The catalog records exact reviewed winget identities and versions, but current
Git/GH installation remains manual: the Git installer can elevate itself and the
reviewed GH installer has machine scope. A manifest's scope label is not evidence
of an unelevated current-user installation. Follow the reported recovery action
to install through your organization's approved process, make the executables
available, and rerun the plan; AI-DLC does not upgrade them implicitly.

Explicitly selected Python provisioning delegates exact pinned Python/uv versions
to mise and verifies them afterward. Unsupported or unqualified selected and
implied modules remain individual blockers, so preparing the supported subset
does not produce complete readiness. Native personal client configuration and
dotfile application are outside this minimal setup lane. No setup step logs in
to providers or clients. Offline readiness still locates tools without running
them; setup's explicit version observations are a separate operation.

Hosted Windows Server CI, clean Windows 11 setup, and native client recognition
are distinct evidence. A passing Server job does not complete the Windows 11 or
interactive client walkthrough; see [release verification](../release-verification.md)
for current qualification status.

### Pending clean Windows 11 teammate walkthrough

This is an execution checklist, not a passing qualification record. Use a clean
Windows 11 x64 account on local NTFS, without administrator elevation or execution
policy changes. Obtain two clean source checkouts at the **same reviewed full
commit** and the original complete release-candidate artifact directory from an
identified workflow run. Do not rebuild or replace candidate bytes. A teammate
may prepare the checkouts with an approved native Git installation; record Git/GH
versions and any manual installation separately. No Python, Node, uv, mise, or
POSIX shell should be preinstalled for the clean-machine claim. If they are
installed but hidden from PATH, record only a cold-PATH result.

In 64-bit Windows PowerShell 5.1, substitute these paths and commit. Both source
paths must contain spaces and a non-ASCII character. The runtime home, consumer
journey, and evidence directory must be new, unused paths. Keep raw logs locally;
share a redacted result with account names/private paths removed.

```powershell
$SourceRevision = 'REPLACE_WITH_REVIEWED_FULL_COMMIT'
$QualificationRoot = Join-Path $env:USERPROFILE 'AI-DLC qualification é'
$SourceA = Join-Path $QualificationRoot 'source one'
$SourceB = Join-Path $QualificationRoot 'source two'
$Artifacts = Join-Path $QualificationRoot 'original candidate'
$Journey = Join-Path $QualificationRoot 'consumer journey'
$Evidence = Join-Path $QualificationRoot 'consumer evidence'
$GitCommandDirectory = 'C:\Program Files\Git\cmd' # Approved native Git only.
$env:AI_DLC_BOOTSTRAP_HOME = Join-Path $QualificationRoot 'runtime one'
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture
$PSVersionTable
Get-Volume -DriveLetter C | Select-Object DriveLetter, FileSystem, DriveType
Get-ExecutionPolicy -List
$env:PATH = "$GitCommandDirectory;$env:SystemRoot\System32\WindowsPowerShell\v1.0"
foreach ($tool in @('python','python3','node','sh','bash','uv','mise')) {
    if (Get-Command $tool -ErrorAction SilentlyContinue) { throw "Cold PATH contains $tool" }
}
foreach ($source in @($SourceA, $SourceB)) {
    if ((git -C $source rev-parse HEAD) -ne $SourceRevision) { throw 'Source revision differs' }
    if (git -C $source status --porcelain) { throw 'Source checkout is dirty' }
}
& "$SourceA\scripts\bootstrap.ps1" -Source -Root $SourceA -Plan
# Review the plan; then run in this same ordinary-user terminal.
& "$SourceA\scripts\bootstrap.ps1" -Source -Root $SourceA
$SourceCli = (Get-Command ai-dlc.exe).Source
$SourcePython = Join-Path (Split-Path $SourceCli) 'python.exe'
& $SourceCli --version
Get-Content -LiteralPath "$env:AI_DLC_BOOTSTRAP_HOME\bin\ai-dlc-selection.json"
```

Stop on an error or unexpected identity; do not treat later output as recovery.
A policy refusal is a recorded blocker, not permission to bypass policy. Bootstrap
may download pinned prerequisites. Network denial or a missing/disallowed Git/GH
installer is also a blocker with its reported recovery action.

Run the [candidate consumer driver](../../scripts/verify_windows_consumer.py)
through that exact source environment. It needs native Git but gives the consumer
an isolated cold PATH; the controller's Python is not a consumer prerequisite.

```powershell
& $SourcePython "$SourceA\scripts\verify_windows_consumer.py" --artifacts $Artifacts --workspace $Journey --evidence $Evidence
if ($LASTEXITCODE -ne 0) { throw 'Candidate consumer verification failed; retain evidence' }
Get-Content -LiteralPath "$Evidence\result.json"
$SelectionBefore = (Get-FileHash "$env:AI_DLC_BOOTSTRAP_HOME\bin\ai-dlc-selection.json").Hash
$AliasBefore = (Get-FileHash "$env:AI_DLC_BOOTSTRAP_HOME\bin\ai-dlc.exe").Hash
& "$SourceB\scripts\bootstrap.ps1" -Source -Root $SourceB
if ((Get-FileHash "$env:AI_DLC_BOOTSTRAP_HOME\bin\ai-dlc-selection.json").Hash -ne $SelectionBefore) { throw 'Shared selection changed' }
if ((Get-FileHash "$env:AI_DLC_BOOTSTRAP_HOME\bin\ai-dlc.exe").Hash -ne $AliasBefore) { throw 'Shared launcher changed' }
Push-Location $SourceA
try {
    & $SourcePython -m pytest -q tests/test_windows_bootstrap.py tests/test_windows_storage.py tests/test_windows_environment.py
    if ($LASTEXITCODE -ne 0) { throw 'Native recovery tests failed' }
} finally { Pop-Location }
```

| Step | Required observation and evidence |
| --- | --- |
| Source/candidate identity | Record full source commit, clean/dirty state, workflow run and original candidate hashes. Version `0.4.0` alone is insufficient; original published v0.4.0 cannot pass this native journey. |
| Consumer driver | Exit 0 plus `result.json` status `passed`, original hashes unchanged, generic/Python required receipts, deliberate failure/recovery and authored-edit refusal. A failed or skipped case stays failed or unqualified. |
| Second checkout | Both selection and shared launcher hashes remain identical; source B prints its own direct executable. Invoke the source A executable retained above when continuing its checks. |
| Sharing, concurrency, interruption and retry | Native tests must actually run, covering held-file publication refusal, concurrent lock exclusion, killed-holder release, authored launcher/profile conflict, and retry. Record test output and skips. These controlled fixtures do not prove that every timing of a real bootstrap interruption recovers. |
| Human fresh terminal/profile | Run the explicit `$PROFILE` preview/apply procedure above through `$SourceCli`; inspect the owned section and retained authored content. **Close the terminal and open the intended PowerShell host yourself.** Inspect `Get-Command ai-dlc`, version and workspace-check provenance. Also resolve `uv` and `mise` and record their pinned versions; in the generated Python project, resolve and check the project-selected Python version. Load the profile twice and confirm PATH is not duplicated. A disallowed or signed profile remains a blocker; use the printed direct executable. |
| Human concurrent bootstrap | In two ordinary PowerShell terminals, start the same full bootstrap command against one disposable bootstrap home while the first process is still running. Record overlapping process IDs, stages and outcomes. Preserve the previous working shared selection, accept either serialized success or an explicit contention refusal, and retry a refused run after the first exits. Verify selected launcher/provenance consistency and both direct executables. If the processes did not overlap, record this case as not exercised. |
| Human interruption | In a disposable second source checkout/runtime journey, interrupt an in-progress bootstrap with Ctrl+C before publication; record the stage. Verify the previous shared selection/launcher bytes and direct command still work, then rerun the same command. If the run completed before interruption, record the case as not exercised. Do not damage a real user's installation to simulate a failure. |

Record each row as passed, failed, blocked, or not exercised, with exact observed
outputs and artifact identities. The driver does not open a desktop terminal,
verify a human's profile experience, authenticate clients, or prove instruction,
skill, or MCP recognition. This walkthrough publishes no package and changes no
remote service. Its Windows 11 evidence remains separate from hosted Windows
Server CI and must be reviewed before updating qualification status.

## Project guidance follows selected capabilities

Shared and native guidance follows the project's selected provider roles. Local
projects keep configuration, durable documentation and required checks without
instructions to use unavailable trackers or finish commands. OpenSpec archive
instructions require the OpenSpec runtime provider; a custom specification
provider retains its own linked instructions. Built-in merge/finish guidance
applies to supported selected SCM/tracker combinations. Removing prose never
relaxes configured checks or runtime completion gates.

For one repository, start with its existing tools and a small `agents.skills`
selection. A separate personal profile or team-source repository is useful when
sharing practices across projects, but is not needed merely to adopt local checks.

## Team sources

A personal profile can subscribe to reviewed team repositories without installing
or running their contents. Add subscriptions to the private profile, then enroll
it as usual. Source definitions cannot be set by project or machine layers:

```toml
[[sources]]
id = "engineering"
git = "https://example.com/team/practices.git"
ref = "main"
roles = []
tags = ["review"]
# layout = "teamai" # default: "ai-dlc"
```

Each source has an exact commit and content digest in the machine enrollment
lock. Rendering verifies this cache offline. `ai-dlc machine sync` fetches and
validates candidates but only previews them; `ai-dlc machine sync --apply`
activates them after machine reconciliation succeeds. Run
`ai-dlc agents render --apply --root PATH` to deliver the selected source revision
to a project. Session-start checks advertised refs within a three-second total
budget and only reports `team source <id> has a newer revision; run
\`ai-dlc machine sync\``. It never fetches source contents, changes locks or writes
client configuration. Offline status and rendering do not inspect remote refs.

A machine binding may add the person's roles with a top-level
`roles = ["developer"]` string list. This is distinct from the profile/project
`[roles]` table selecting providers; machine roles never replace that table.
Role, namespace and tag identifiers may contain lowercase letters, digits,
hyphens and underscores (for example `hai_dev`). Source `roles` and machine roles
are combined, while source `tags` select tag
subscriptions. Items without selectors are universal; other items require any
matching role or tag. Validation applies to every item before filtering, so an
unselected item cannot hide unsafe content. Unenrollment or role deselection
removes only previously owned source outputs on the next render. Source skill
names cannot collide with any shipped or selected bundled skills, other source skills,
or authored client skills; even an identical authored file remains unowned.
Edited owned outputs are also preserved through refusal. Source rules appear in
AGENTS.md's owned section, and skills also appear in selected client skill files.
Shared guidance indexes each selected team skill by name, source, bounded
description and links to its complete native skill files. Rules remain inline.
Read an applicable skill's linked file before using it; file generation alone
does not establish native discovery or authentication. Codex and Antigravity
share `.agents/skills`; Claude uses `.claude/skills`. An explicit client render
indexes that operation's destinations. When no client is rendered, full skill
bodies remain inline so the selected instructions are still accessible.

An ordinary render upgrades intact generated sections to this index without
changing source locks or skill bytes. Edited owned sections and authored conflicts
still refuse. Narrow role/tag subscriptions and `agents.skills` keep selection
relevant; measured guidance bytes are not evidence of actual model token savings.

The native layout contains `manifest.toml`, `skills/<name>/SKILL.md`,
`rules/<name>.md`, and optional `mcp/servers.toml` and `hooks/hooks.toml`.
Every exported item is listed in the manifest; other files are refused:

```toml
schema = 1

[[items]]
kind = "skill"
name = "team-review"
path = "skills/team-review/SKILL.md"
roles = ["developer"]
tags = ["review"]

[[items]]
kind = "rule"
name = "review"
path = "rules/review.md"

[[items]]
kind = "mcp"
name = "team-tools"
path = "mcp/servers.toml"

[[items]]
kind = "hook"
name = "session-context"
path = "hooks/hooks.toml"
```

`mcp/servers.toml` declares `[[servers]]` entries with `id`, `command` and optional
`args = ["serve"]`. Commands are portable executable names; AI-DLC imports the
configuration without executing the command. URLs, headers, environment values,
credential arguments and machine paths are refused. Hook content is only
`features = ["session-context"]` or other existing `bound-push` and
`stop-reminder` features. Arbitrary shell hooks are refused. The selected client's
configured version must already support those features in AI-DLC's capability
matrix. All source paths must be regular UTF-8 files without symlinks or execute
bits, up to 2 MiB each and 10 MiB total, with at most 1,024 files and 16 path
segments. Structured manifests are limited to 1 MiB. `env/` directories are
refused, and credential diagnostics name the source path without echoing values.

Set `layout = "teamai"` to read an existing
[Tencent teamai repository](https://github.com/Tencent/teamai-cli). AI-DLC imports
flat or namespaced skills, flat rules, `culture.md` as the `culture` rule, and
`mcp/mcp.yaml`'s `servers` list with `name`, optional `transport: stdio`, `command`
and `args`. It reads role/tag metadata from `teamai.yaml` when present, Markdown
frontmatter, and the current upstream `manifest/roles.yaml` role-to-skill-namespace
mapping and `tags.yaml` skill/rule tag maps. AI-DLC applies the selection rule
above rather than upstream's permissive no-subscription fallback. Hooks, agents
and docs are ignored with notes after safety validation; `env/` and embedded
MCP token/environment values are refused. YAML aliases and duplicate keys are
refused. This is a deliberately limited source reader: it does not install
teamai, execute its hooks, import packages, write back, or access its dashboards.
