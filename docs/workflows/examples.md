# Example workflows

## Take a ticket through delivery

With tracker and SCM connections configured:

1. Draft work from an existing issue: `ai-dlc work new improve-setup --from-issue 42`
2. Review `.ai-dlc/work/improve-setup.toml`: set scope and acceptance criteria,
   decide whether a specification is required, link it when needed, and set
   `reviewed = true`.
3. Publish and start it:
   ```sh
   ai-dlc work publish improve-setup
   ai-dlc work start improve-setup
   ```
4. Implement, commit, and update the affected documentation. Then run
   `ai-dlc project check --required`. If this work requires OpenSpec, finalize it
   with `ai-dlc work archive` before review.
5. Push the bound branch, then open its PR: `ai-dlc work pr improve-setup`
6. Push the work-record link commit that `work pr` created, then review and merge.
7. From a checkout at the merge commit, after CI succeeds, run
   `ai-dlc work finish improve-setup`.

Finish validates the required specification, PR merge and exact merged-revision
CI evidence, plus configured deployment gates. `work status` is a local
inspection, not a fresh tracker read.

## Keep project documents useful

```sh
ai-dlc docs init                  # Preview missing navigation.
ai-dlc docs check                 # Inspect ownership, coverage, and links.
ai-dlc docs search "authentication"
ai-dlc docs review --base origin/main
```

Use reviewed dispositions and `ai-dlc docs gate` to keep documentation current
with a change. Project-document access covers repository files; private vault
access uses separate knowledge tools. The [documentation guide](https://github.com/Sean-Koval/ai-dlc/blob/main/project-templates/project/docs/documentation-guide.md)
covers review, MCP search/read, and optional Obsidian portals and mounts.

## Start an FDE engagement

```sh
ai-dlc fde scaffold customer-delivery --title "Customer delivery" --dry-run
ai-dlc fde scaffold customer-delivery --title "Customer delivery"
ai-dlc fde check customer-delivery
```

This creates a charter and Discover → Frame → Design → Build → Deploy → Enable →
Expand landing pages under `docs/fde_engagements/`. Stage checks require earlier
exit criteria and recorded evidence before downstream activation. See the
[FDE guide](../runbooks/fde-documents.md) for configuration and stage metadata.
Confluence publication and synchronization remain unimplemented.
