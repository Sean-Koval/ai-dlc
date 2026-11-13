---
id: short-slug                # draft slug; ACT-NNNN is assigned at merge
type: action
scope: team                   # personal | project | team
status: open                  # the tracker's own status
date: YYYY-MM-DD
owner: github-login           # who owes it
sources:                      # what it came from (OKF sources)
  - {id: SRC-NNNN, resource: path/or/url}  # add hash: sha256:<64 hex> for a derived_from target
links: []                     # [{type: derived_from, target: SRC-NNNN}, {type: belongs_to, target: KAN-NNN}]
title: Short title            # shown in the OKF index
description: One line for the index
# stale_after: YYYY-MM-DDT00:00:00Z       # due date
# label: internal             # internal | confidential
# tags: [topic]
# verified: {by: "human:github-login", at: YYYY-MM-DDTHH:MM:SSZ}
---
# Who owes what

## Done when
