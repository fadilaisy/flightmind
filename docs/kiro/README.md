# Recording our Kiro work

## Commit trailers

Every commit ends with one `Kiro:` trailer.

| Trailer | Meaning |
| --- | --- |
| `Kiro: spec <spec>/<task>` | Kiro implemented a spec task |
| `Kiro: vibe` | Kiro wrote or edited the change in a chat session |
| `Kiro: hook` | a hook in `.kiro/hooks` produced it |
| `Kiro: none` | a person typed it without Kiro |

Rule: who typed the diff decides the trailer.

Install the hooks once with `scripts/install-hooks`. It sets `core.hooksPath` to `.githooks`, so
`.githooks/commit-msg` refuses a commit without a valid trailer (merge, `fixup!` and `squash!`
commits pass), and `commit.template` to `.gitmessage`. The Kiro IDE hook
`.kiro/hooks/commit-trailer.kiro.hook` also checks the trailer when an agent turn ends.

When Kiro implements a task from a spec's tasks.md, use spec <spec>/<task>, even if you ran it from a chat session. Use vibe for chat work that isn't a spec task.

If a trailer is wrong or missing, do not rewrite the commit. Add a line to the "Trailer
corrections" section of `KIRO.md`; `scripts/kiro-stats` and `scripts/kiro-timeline.mjs` apply it
when they count. Line format: `sha | was | now | reason`.

- `was` is what the commit's own trailer says (`spec`, `vibe`, `hook` or `none`). Use `missing`
  when the commit has no `Kiro:` trailer at all.
- `now` is one of the four types. Use `spec` or `vibe` only with evidence (a spec task, a session
  log); otherwise use `none` and write "unclear" in the reason.
- The correction counts only while the commit's real trailer still says `was`.

`scripts/kiro-stats` prints `commits_unclassified=<n>`: commits with no trailer and no correction.
It should be 0.

## Four layers

Four layers, from automatic to manual:

1. **The repo.** `.kiro/` is committed from day one. Specs keep their ticked `tasks.md`.
   Every commit ends with a `Kiro:` trailer (`git config commit.template .gitmessage`).
2. **`KIRO.md`.** The "log ticked task" hook adds one line per finished spec task. Work done
   in chat gets a line too, with the Jira key and "(chat)".
   Add the "fixed by hand" part yourself if the hook left it out.
3. **Session notes.** When a chat or spec run is worth telling, save the prompt, the result
   and a screenshot as `sessions/YYYY-MM-DD-topic.md` (template in `sessions/TEMPLATE.md`).
4. **Clips.** 30 to 120 seconds, 1080p, Kiro full screen, no music. Name
   `YYYY-MM-DD_role_feature.mp4`, upload to the shared Drive folder, add a row to `clips.md`.

Every Sunday, Role 1 runs `scripts/kiro-stats`, pastes the output into `KIRO.md` and marks
the two best clips of the week as video candidates.

`setup-prompts.md` holds the prompts for creating our hooks, the reviewer agent and the
specs inside Kiro. Create them in Kiro rather than by hand, and record the first one: the
creation itself is evidence for the write-up.

## Refresh the evidence

Run these from the repo root and commit the result.

| What | Command | Writes |
| --- | --- | --- |
| Kiro CLI session logs | `python scripts/kiro-sessions-export --also-cwd <other clone of this repo>` | `docs/kiro/sessions/cli/` (one redacted log per session and an index) and `docs/kiro/sessions/prompts/` (prompt files the sessions read) |
| Timeline for the Built with Kiro page | `cd web && npm run kiro:timeline` | `web/src/kiro/timeline.json` (commits, mix, specs, hooks) |
| Counts for the Sunday review | `scripts/kiro-stats` | prints to the terminal; paste into `KIRO.md` |

The session export keeps sessions whose working folder is this repo or one given with
`--also-cwd`. It replaces your home folder, temp folders, secrets and email addresses with `~`,
`<temp>` and `<redacted>`. Check the output with a grep for your user name before committing.
Regenerate the timeline after every commit you want the page to show; the page says which commit
it was generated from.
