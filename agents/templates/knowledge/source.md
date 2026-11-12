---
id: short-slug                # draft slug; SRC-NNNN is assigned at merge
type: source
scope: personal               # personal | project | team
status: raw                   # raw | processed | expired (after 30 days)
date: YYYY-MM-DD
owner: github-login
source: path/or/permalink     # where the original lives
links: []                     # [{type: belongs_to, target: project-slug}]
description: One line for the index
schema_version: 1             # source envelope version
revision: "1"
provider: zoom                # zoom | meet | symphony | notes | ...
title: Meeting or thread title
observed_at: YYYY-MM-DDTHH:MM:SS+00:00
obligations: []               # [{intent_key: send-report, title: Send the report, status: open}]
# url: https://example.invalid/permalink
# labels: [internal]
---
Transcript, thread or marked note lines.
