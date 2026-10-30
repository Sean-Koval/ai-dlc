# Terms

What the recurring words in these docs mean, for a reader new to ai-dlc. The
[architecture](../architecture.md) shows how the parts fit.

| Term | Meaning here |
| --- | --- |
| Workflow plugin | `plugins/ai-dlc-workflow/`: the optional Claude Code plugin (with a Codex form) carrying the workflow guidance as a skill, ten more skills and three hooks. Off by default; a team harness decides where it is on. See [Workflow plugin](../workflows/workflow-plugin.md). |
| Team harness | A git repository of the native files a team's agents run with, pinned by hangar's `harness.lock`. It pins the workflow plugin as `plugin:ai-dlc-workflow@<marketplace>`. ai-dlc publishes into it but does not define it. |
| Managed section | The block between `<!-- ai-dlc:begin <digest> -->` and `<!-- ai-dlc:end -->` in an adopted repository's AGENTS.md, rendered by `ai-dlc agents render` and guarded by `.ai-dlc/agent-ownership.json`. |
| Profile | A versioned `ai-dlc-profile.toml` in a private Git repository: portable modules, client settings and named credentials. |
| Machine binding | One machine's own paths, account selections and credential environment-variable names; never shared. |
| Enrollment | Binding a machine to a profile at a pinned revision (`ai-dlc machine enroll`); `machine sync` moves it. |
| Provisioning | Installing a profile's modules and client configuration on a machine (`ai-dlc setup plan`, then `ai-dlc setup apply`). |
| Work record | `.ai-dlc/work/<id>.toml`: reviewed scope bound to a tracker item, branch, specification and pull request. |
| Receipt | The JSON `ai-dlc project check` writes for a commit: each required check's outcome. `work finish` needs a passing one for the merge commit. |
| Finish gates | `specification-current`, `pr-merged` and `ci-green`; `work finish` closes the ticket only when all pass. |
| Tracker writes | `[work] tracker_writes`: `lifecycle` (default) or `finish-only`, where hangar intake owns starting work. |
| Documentation gate | `ai-dlc docs gate`: every changed catalogued document has a current reviewed disposition and no new objective defect. |
| Knowledge note | Markdown with the frontmatter in `contracts/knowledge-note.schema.json`; used by learnings and decision records. |
| Frozen | Kept working and open to bug fixes, but closed to new features (ADR 0001's frozen list). |
| Tower | The suite's governance plane: policy decisions, approvals and receipts. ADR 0001 calls it by its earlier name, the governed workspace. |

## "Capabilities"

The word means eight different things in this repository. Use the specific term in
the first column instead of a bare "capability"; the files and options keep their
current names ([#203](https://github.com/Sean-Koval/ai-dlc/issues/203) tracks any
rename).

| Say | What it is | Where |
| --- | --- | --- |
| Project role or feature | A choice made at project creation or adoption: the six roles (`specs`, `tracker`, `knowledge`, `scm`, `deploy`, `agent-client`) and the optional features `backend` and `frontend` | `--capability` on `project init` and `project adopt`; the Copier question `capabilities` in `project-templates/copier.yml`; `CAPABILITIES` and `OPTIONAL_CAPABILITIES` in `setup/templates.py` |
| Tracker lifecycle operations | What a tracker adapter declares it can do (an in-progress state, close), answered through the provider contract's `capabilities` operation | `contracts/capabilities.*.schema.json`; [Tracker capabilities and connection](../architecture.md#tracker-capabilities-and-connection) |
| Execution target properties | Filesystem, network, hooks and persistence of each `project setup --target` | `targets/capabilities.toml` (`local`, `github-actions`) |
| Client hook floor | The hooks each agent client supports and its minimum version | `agents/capabilities.toml` |
| Feature pack | The optional frontend and backend scaffolding with their checks | OpenSpec specs `frontend-capability-pack` and `backend-capability-pack` |
| OpenSpec capability | One specification directory under `openspec/specs/` (47 today); the freeze stops new ones outside the in-scope list | `openspec/specs/<name>/spec.md` |
| Component contract | How a selected role resolves to installation modules and provider guidance | `modules/components.json`; OpenSpec `component-capability-contract` |
| Plain English | "Something the product can do" in prose | Prefer "feature" |
