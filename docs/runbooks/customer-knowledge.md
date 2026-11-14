# Customer knowledge repositories

Keep one customer's records in a repository of their own, and move a lesson to
the team only as a sanitised summary. The rules are in
[ADR 0007](../decisions/0007-customer-knowledge-repositories.md).

## Create the repository

```sh
ai-dlc knowledge init --customer acme --codeowner @your-org/fde --deny "Acme Corp" --dry-run
ai-dlc knowledge init --customer acme --codeowner @your-org/fde --deny "Acme Corp"
```

Run it outside any checkout. It makes `acme-knowledge/` its own git repository, with
a declared `knowledge.toml`, `deny-terms.txt`,
CODEOWNERS, a README, the check workflow, `projects/acme/` and `inbox/`. It sets no
`[wiki]`, so nothing renders to Confluence.

Its CI pins ai-dlc's workflows to the installed release tag. Pass `--ai-dlc-ref`
with a later tag or a commit to change it; never a branch. Without it, init warns.

Host it where the contract says: a private repository on the company's GitHub, or
the customer's own systems. Add every customer name, host and identifier you know
to `deny-terms.txt`, one per line.

Point the transcript route at the checkout with `KNOWLEDGE_REPO_ACME`. A checkout
that does not declare `project = "acme"` receives nothing. List your own people in
the team repository's `[transcripts] internal`. A meeting that matches no customer
and has anyone else in it goes nowhere.

## Promote a lesson

Write the summary in your own words, with no customer names, quotes, hosts or
paths. Then run it from the customer repository:

```sh
ai-dlc knowledge promote LES-0004 --to ../team-knowledge \
  --summary summary.md --title "Ask for maintenance windows" --owner sean --dry-run
```

Without `--dry-run`, it commits a team Source and a derived team record on a new
branch, `promote/<slug>`, of the team repository. Your checkout and its current
branch do not change, and nothing is pushed. Review the branch, push it and open
a pull request as usual.

A refusal names its reason. It may be a deny-list term, a web address, a customer
path, or eight words in a row from the customer record. Look-alike letters, a word
mixing two alphabets, `A.C.M.E.` and `AcmeCorp` count. Reword and run again.
