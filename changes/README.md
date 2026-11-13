# Changelog fragments

A PR adds its changelog entry here, as `changes/<KEY>.md` (its ticket key, such as `KAN-481`), and never edits
`CHANGELOG.md`. Two PRs then can't conflict on the changelog. Write the entry as one or more `- ` bullets. The section
is Changed unless the name says otherwise: `changes/<KEY>.added.md`, `.fixed.md`, `.removed.md`, `.deprecated.md` or
`.security.md`. At release, `python scripts/collect_changes.py --write` folds the fragments into `CHANGELOG.md` and
deletes them; without `--write` it checks them.
