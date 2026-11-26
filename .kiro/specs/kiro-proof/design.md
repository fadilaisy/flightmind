# Design: kiro-proof (SCRUM-70)

## Pieces

| Piece | File | Notes |
| --- | --- | --- |
| Trailer check | `.githooks/commit-msg`, `scripts/install-hooks` | POSIX sh, runs in Git for Windows. Pattern: `^Kiro: (spec [a-z0-9-]+/[A-Za-z0-9.,_-]+\|vibe\|hook\|none)$`. `#` lines ignored. |
| IDE hook | `.kiro/hooks/commit-trailer.kiro.hook` | `agentStop`, `askAgent`; same JSON shape as the other hooks. |
| Stats | `scripts/kiro-stats` | Trailer counts plus corrections. `missing` is a valid "was". Prints `commits_unclassified`. |
| Session logs | `scripts/kiro-sessions-export` | Python standard library only. Reads `~/.kiro/sessions/cli/*.json` and `*.jsonl`. Redacts home path, temp paths, secrets and emails. Output in `docs/kiro/sessions/cli/`, prompt files copied to `docs/kiro/sessions/prompts/`. |
| Timeline data | `scripts/kiro-timeline.mjs`, `web/src/kiro/timeline.json` | Node ES module. Parsing lives in `web/src/domain/kiroTimeline.ts` and is unit tested; the script uses the same logic. |
| Page | `web/src/views/KiroView.tsx`, `?tab=kiro` | Reads the JSON at build time. Needs no API. Text in `strings.ts`. Card and badge styles reuse `tokens.css`. |
| Index | `KIRO.md` "Evidence", `docs/kiro/README.md` | Links to all of the above, with the current `kiro-stats` output. |

## Decisions

- Old commits are not rewritten. A commit with no trailer gets a `sha | missing | <type> | reason` line.
  A commit is classified as `spec` or `vibe` only with evidence; otherwise `none` with "unclear".
- The page imports a generated JSON file, so it works offline and on the Vercel build without git.
- `?tab=kiro` is handled in `App.tsx` before the events and recording gate, so the page renders
  when the API is down.
- Session logs are redacted before writing; the grep check for `Pongo`, `@gmail`, `sk-`, `AKIA`,
  `ghp_` and `BEGIN` is part of task 3.
