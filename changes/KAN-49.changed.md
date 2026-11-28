- A tagged release's GitHub notes are now its `## [<version>]` section of `CHANGELOG.md`, with relative links made
  absolute at the tag, followed by the install note. `python scripts/collect_changes.py --release-notes <version>`
  prints them, and the `Release` workflow refuses a tag whose version has no section (KAN-49).
