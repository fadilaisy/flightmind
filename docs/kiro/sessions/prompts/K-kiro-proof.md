# Kiro prompt K: make our Kiro usage verifiable (SCRUM-70)

You are working in this repository on branch `claude/project-thread-zvb5hn` (already checked out, based on origin/main). Do not switch branches, do not push, do not touch `contracts/`, `services/`, `infra/`, `.kiro/agents/` or `.kiro/settings/mcp.json`.

Goal: today our Kiro usage is claimed in `KIRO.md`. Make it verifiable from the repo itself: committed `.kiro/`, a `Kiro:` trailer on every commit (checked by a hook), exported Kiro CLI session logs, and a "Built with Kiro" page in the web UI that cites every number back to a spec file or a commit on GitHub. Read `KIRO.md`, `docs/kiro/README.md`, `.gitmessage`, `scripts/kiro-stats`, `.kiro/steering/*.md` (especially `ui.md` and `structure.md`) and `web/src/App.tsx`, `web/src/views/Shell.tsx`, `web/src/strings.ts`, `web/tests/wording.test.ts` before you start.

Commit rules: one commit per task below. Message format `kiro-proof/<n>: <summary>` and the last line is the trailer `Kiro: spec kiro-proof/<n>` (task 0 uses `Kiro: spec kiro-proof/0`). Never add any Co-Authored-By line. Tick each task in `.kiro/specs/kiro-proof/tasks.md` in the same commit that does it, and add one line per task to `KIRO.md` in its usual format (`date | Fadil | kiro-proof/<n> | what Kiro did | fixed by hand`), with "nothing" as fixed by hand.

## Task 0: spec
Write `.kiro/specs/kiro-proof/requirements.md`, `design.md` and `tasks.md` (tasks 1 to 6 below, unticked; tick task 0 if you list it). Requirements in EARS style, referencing SCRUM-70. Keep it short.

## Task 1: trailer check
- `.githooks/commit-msg` (POSIX sh, works in Git for Windows): refuses a commit unless the message has a line matching `^Kiro: (spec [a-z0-9-]+/[A-Za-z0-9.,_-]+|vibe|hook|none)$`. Lines starting with `#` are ignored. Merge commits (`.git/MERGE_HEAD` exists), and messages starting with `fixup!`, `squash!` or `Merge ` are allowed through. The error message says which four forms are valid and points to `docs/kiro/README.md`.
- `scripts/install-hooks` (bash): runs `git config core.hooksPath .githooks` and `git config commit.template .gitmessage`, prints what it did. Make both files executable in git (`git update-index --chmod=+x`).
- `.kiro/hooks/commit-trailer.kiro.hook`: Kiro IDE hook, `"when": {"type": "agentStop"}`, `askAgent` prompt: if you made a git commit in this turn, check `git log -1 --format=%B` ends with a valid `Kiro:` trailer per docs/kiro/README.md; if not, tell the user which trailer it should have and do not amend pushed commits. Same JSON shape as the other hooks in `.kiro/hooks/`.
- Run `scripts/install-hooks` once in this clone so your own later commits are checked. Show that a commit without a trailer is refused (try `git commit --allow-empty -m "test"` and paste the refusal into your final summary; it must fail).

## Task 2: backfill and stats
Old commits are never rewritten. Extend the existing "## Trailer corrections" mechanism:
- A correction line may use `missing` as its "was" value, meaning the commit has no `Kiro:` trailer.
- Classify every non-merge commit reachable from HEAD that has no trailer (`git log --no-merges --format='%h|%(trailers:key=Kiro,valueonly)|%s'`) by reading its message and `git show --stat`. On main there should be about four: the initial commit and a README edit (both `none`), and two `docs(kiro)` commits adding Figma reference screenshots and design context (`none`: added by hand, not written by Kiro). Add one correction line each with a reason. If a commit is genuinely unclear, use `none` and say "unclear" in the reason; never guess `spec` or `vibe` without evidence.
- `scripts/kiro-stats`: count per type from trailers of non-merge commits plus corrections (including `missing`), and print `commits_unclassified=<n>` (trailer missing and no correction), which must be 0 after your corrections. Also print the share of each type in percent. Keep the existing output keys so the Sunday review still works.

## Task 3: session logs
`scripts/kiro-sessions-export` (Python 3, standard library only, run with `python scripts/kiro-sessions-export`):
- Reads Kiro CLI v2 sessions from `~/.kiro/sessions/cli/*.json` + matching `*.jsonl`. Keeps sessions whose `cwd` (in the .json) is this repo's root or one of the extra paths given with `--also-cwd PATH` (repeatable; compare case-insensitively, normalise slashes, strip a leading `\\?\`).
- Writes one markdown file per session to `docs/kiro/sessions/cli/<YYYY-MM-DD>-<first 8 chars of id>.md`: header (session id, created and updated time in UTC, number of prompts, tool calls), then in order: each user prompt in full, each assistant text block in full, each tool call as one line `tool <name>: <short input, max 200 chars>`, and tool results only when they are errors (first 300 chars). Skip `thinking` blocks and redacted content.
- When a prompt or a tool call reads a prompt file (a path ending in `\prompts\<name>.md`), copy that file to `docs/kiro/sessions/prompts/<name>.md` (if it still exists) and write the path in the log as `docs/kiro/sessions/prompts/<name>.md`.
- Redaction before writing: replace the user's home directory (`Path.home()`, both slash styles) with `~`, temp scratchpad paths with `<temp>`, and anything that looks like a secret (`sk-[A-Za-z0-9_-]{16,}`, `AKIA[0-9A-Z]{16}`, `ghp_[A-Za-z0-9]{20,}`, `xox[bp]-[A-Za-z0-9-]+`, `-----BEGIN [A-Z ]*PRIVATE KEY-----` blocks, values of `ANTHROPIC_API_KEY=`/`*_TOKEN=`/`*_SECRET=`) with `<redacted>`. Also redact email addresses.
- Writes `docs/kiro/sessions/cli/README.md` as an index table: date, session id, first prompt (one line), prompts, tool calls, link.
- Re-running is idempotent (same input gives same files).
Run it with `--also-cwd` set to the folder `~\OneDrive\Documents\flightmind kiroween\flightmind` (the main checkout, where most sessions ran) in addition to this clone. Before committing, grep the output for `Pongo`, `@gmail`, `sk-`, `AKIA`, `ghp_` and `BEGIN` and fix the redaction if anything shows up. Commit the generated files. If a single session file is over 1 MB of markdown, cut tool-call lines after the first 2000 and say so at the end of that file.
Update `docs/kiro/sessions/2026-11-14-scrum-31-32-chat.md` only if a matching CLI session exists; otherwise leave it.

## Task 4: timeline data
`scripts/kiro-timeline` (Node, ES module, no new dependencies, `node scripts/kiro-timeline.mjs` is fine) writes `web/src/kiro/timeline.json` from git history (`git log` on HEAD, non-merge commits), the trailer corrections in KIRO.md, and `.kiro/specs/*/`:
```
{ "generatedAt": ISO, "head": sha, "repo": "https://github.com/fadilaisy/flightmind",
  "mix": { "spec": n, "vibe": n, "hook": n, "none": n },
  "specs": [ { "name", "title" (first # heading of requirements.md), "tasksDone", "tasksTotal",
               "files": { "requirements", "design", "tasks" } (repo-relative paths),
               "commits": [sha...] } ],
  "commits": [ { "sha", "short", "date" (YYYY-MM-DD), "author", "subject", "kind", "spec"?, "task"?, "corrected"? (true when kind came from KIRO.md) } ],
  "hooks": [ { "file", "name", "when" } ], "steering": [ "file" ], "sessions": n (files in docs/kiro/sessions/cli, minus README) }
```
Commits newest first. `spec` commits are grouped into their spec by the trailer's spec name. Put the pure parsing (trailer line, corrections table, tasks.md counting) in `web/src/domain/kiroTimeline.ts` so it can be unit tested, and have the script import the same logic or duplicate it minimally; tests cover: trailer parsing including `spec web-ui/3`, `spec agent-mcp/10-21`, a correction with `missing`, and task counting. Add `"kiro:timeline": "node ../scripts/kiro-timeline.mjs"` to web/package.json scripts. Regenerate and commit the JSON as the last step of task 6 too, so it includes this work.

## Task 5: Built with Kiro page
A new view `web/src/views/KiroView.tsx`, shown at `?tab=kiro` with no recording needed (it must render even when the API or the recording gate is not ready). Add a "Built with Kiro" entry to the app bar so people can reach it, styled like the existing tabs (follow `ui.md` and `web/src/styles/tokens.css`; reuse existing card styles; no new colours unless tokens lack one). Content, all text in `strings.ts`:
- Title "Built with Kiro" and one line: every number on this page links to the commit or spec file it comes from.
- Mix card: four counts (spec, vibe, hook, none) with a simple horizontal stacked bar, total commits, and "generated from <short head sha>" linking to that commit.
- Spec cards, one per spec: title, `tasksDone / tasksTotal` tasks, links to requirements, design and tasks on GitHub (`<repo>/blob/main/<path>`), and the number of commits with a link that expands the list (each commit: short sha linking to `<repo>/commit/<sha>`, date, subject).
- Timeline: commits grouped by date, newest first, each with a small kind badge, short sha link, subject. A filter for kind (all, spec, vibe, hook, none). Corrected commits show "classified in KIRO.md" with a link to `<repo>/blob/main/KIRO.md`.
- Footer links: hooks (each file), steering files, session logs (`docs/kiro/sessions/cli/README.md`), and `KIRO.md`.
Tests in `web/tests/kiro.test.tsx`: renders from a small fixture timeline, shows the mix counts, a spec card links to its tasks.md, a commit links to its GitHub commit URL, the kind filter hides other kinds, and `?tab=kiro` renders without a recording. The existing wording test must still pass. `npm test` and `npm run build` in `web/` must pass.

## Task 6: KIRO.md as the index
At the top of `KIRO.md`, under the title, add a short "Evidence" section linking: `.kiro/specs/` (list each spec), `.kiro/hooks/`, `.kiro/steering/`, `.githooks/commit-msg` and `scripts/install-hooks`, `scripts/kiro-stats` (with its current output pasted in a code block), `docs/kiro/sessions/cli/README.md`, `docs/kiro/clips.md`, and the page (`https://flightmind.vercel.app/?tab=kiro`). Update `docs/kiro/README.md`: the trailer table stays, add "Install the hooks once with `scripts/install-hooks`", the `missing` correction value, and how to refresh session logs and the timeline. Regenerate `web/src/kiro/timeline.json`, run `npm test` and `npm run build` in `web/`, then commit.

## Finish
Print a summary: the commits you made (`git log --oneline origin/main..HEAD`), the `scripts/kiro-stats` output, the refused test commit output from task 1, test and build results, and anything you could not do.
