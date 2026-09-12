# Retry Project membership readback before reporting uncertain attachment

## Why
`GitHubProject.attach` adds an issue to the Project and immediately paginates Project items to confirm membership. GitHub does not always expose a new item in that first read. On 2026-09-11 the first `ai-dlc work publish` failed with `Project attachment remains uncertain` for the issues later numbered #39-#42 and again for #48; each issue existed and was attached, and a plain retry reconciled membership without creating a duplicate.

## What Changes
- Membership readback SHALL be retried a bounded number of times with backoff when the mutation returned an item identity and membership is not yet visible.
- Persistent absence, a different item identity or ambiguous membership SHALL still fail and leave the operation uncertain.
- The retry SHALL NOT repeat the attachment mutation, so no duplicate item can be created.

## Capabilities
### Modified Capabilities
- github-ticket-workflows: Delayed Project membership visibility is distinguished from an uncertain attachment.

## Impact
The Projects adapter and its fixtures. No issue lifecycle, journal semantics, finish gate or Project status behavior is changed, and no additional attachment request is sent.
