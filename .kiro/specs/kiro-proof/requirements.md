# Requirements: kiro-proof (SCRUM-70)

Goal: our Kiro usage is verifiable from the repository itself, not only claimed in `KIRO.md`.
Owner: Fadil. Folders: `.githooks/`, `.kiro/hooks/`, `.kiro/specs/kiro-proof/`, `scripts/`, `docs/kiro/`,
`web/`, `KIRO.md`. Trailer rules: `docs/kiro/README.md`.

## Requirements (EARS)

1. When a commit message is saved, the `commit-msg` hook shall refuse the commit unless it has a
   line `Kiro: spec <spec>/<task>`, `Kiro: vibe`, `Kiro: hook` or `Kiro: none`. (SCRUM-70)
2. While a commit is a merge, or its message starts with `fixup!`, `squash!` or `Merge `, the
   hook shall let it through.
3. When a person runs `scripts/install-hooks`, the script shall point `core.hooksPath` at
   `.githooks` and `commit.template` at `.gitmessage`.
4. When an agent turn ends, the Kiro IDE hook `commit-trailer` shall ask the agent to check that
   any commit made in the turn has a valid trailer.
5. If a commit has no trailer, then `scripts/kiro-stats` shall count it through a correction line
   in `KIRO.md` whose "was" value is `missing`, and shall print `commits_unclassified=<n>`.
6. When `scripts/kiro-sessions-export` runs, it shall write one redacted markdown log per Kiro
   CLI session for this repository, plus an index, and shall give the same files on a re-run.
7. When `scripts/kiro-timeline` runs, it shall write `web/src/kiro/timeline.json` from git
   history, the corrections in `KIRO.md` and `.kiro/specs/*/`.
8. When a visitor opens `?tab=kiro`, the web app shall show the "Built with Kiro" page without
   needing a recording or a working API.
9. The page shall link every number to the commit or spec file on GitHub it comes from.
10. `KIRO.md` shall list the evidence (specs, hooks, steering, trailer check, stats, session
    logs, clips and the page) near the top.

## Not in scope

- Rewriting old commits. Wrong or missing trailers are fixed only by correction lines.
- Changes to `contracts/`, `services/`, `infra/`, `.kiro/agents/` or `.kiro/settings/mcp.json`.
