# GitHub source control

This SCM role uses GitHub pull requests and exact merged-revision CI evidence,
independently of the selected issue tracker. Configure `[scm] repository` as the
intended `owner/repo`; `providers.github.repository` is not the SCM setting.
The existing core requirement checks that `git` and `gh` are on PATH.

Local executable/configuration readiness does not verify GitHub authentication,
repository permissions, PR merge or CI receipts. Use the intended account's
approved `gh` authentication separately. Preserve the configured specification,
PR-merge and exact merged-CI finish gates. Do not borrow the engine repository's
personal issue/Project identity for a work repository.

`ai-dlc work pr <id>` uses the optional `pull_request_create` SCM operation to open a PR in the configured repository for the bound branch. Push the branch first; the adapter refuses an absent upstream and never pushes implicitly. The service journals creation, links the URL, and commits only the work record. Push that link commit before review. Retry returns a linked or durably recorded URL; uncertain creation requires inspecting the SCM and linking the existing PR.
