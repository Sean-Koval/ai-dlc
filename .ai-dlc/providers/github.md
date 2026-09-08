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
