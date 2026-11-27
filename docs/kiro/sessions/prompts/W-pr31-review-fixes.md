# PR #31 review fixes (SCRUM-70, Built with Kiro page)

You are in a separate git worktree of FlightMind on branch `role1/scrum-70-built-with-kiro` (PR #31).
Stay in this folder. Do not switch branches, do not push, do not touch any other checkout.
`web/node_modules` is already installed. The demo is recorded today, so keep the scope to the steps below.

## 1. Merge main into this branch

Run `git fetch origin main` then `git merge --no-ff origin/main`. Three files conflict. Resolve them by keeping both sides:

- `KIRO.md`: keep every log line from both sides, in date order inside each section. Keep this branch's
  `## Trailer corrections` section and evidence index unchanged. Lose no line from either side.
- `web/src/strings.ts`: `TAB_LABEL` keeps main's order (load, preview, clean, events, trajectory, records, export)
  and adds `kiro: "Built with Kiro"` as the last entry. `STR` keeps every key from both sides.
- `web/src/App.tsx`: take main's version, then apply step 2.

Commit the merge (merge commits need no trailer).

## 2. Make the Built with Kiro tab work with main's recording gate

Main's `App.tsx` now checks a recording first (`gate`): while it is `checking` it shows a spinner, when it is `load`
it shows the Load screen, and it passes `activeTab="load"` to `Shell`. So `?tab=kiro` without a ready recording shows
the Load screen with the Load tab highlighted, not the Kiro page. Fix:

- In `body(tab)`, the very first line returns `<KiroView />` when `tab === "kiro"`, before any `gate` check.
  Keep the comment that the page needs neither a recording nor the API.
- Pass `activeTab={gate.kind === "load" && tabParam !== "kiro" ? "load" : null}` to `Shell`, so the Kiro tab stays
  highlighted when no recording is loaded.
- Do not change anything else in App.tsx or Shell.tsx.

## 3. Test it

In `web/tests/smoke.test.ts` add a case that opens `?tab=kiro` with **no** recording seeded (clear
`localStorage` first and do not add `&recording=`), and checks that the page shows "Built with Kiro", that the tab
button `#tab-kiro` has `aria-selected="true"`, that no Load screen is shown, and that console.error is not called.
Keep the existing four cases passing.

Run from `web/`: `npm test` and `npm run build`. Both must pass. If a test fails, fix the cause, not the test.

## 4. Refresh the timeline

From `web/` run `npm run kiro:timeline` so `web/src/kiro/timeline.json` counts the commits that came in from main
(upload UI, load page). Report the line it prints (commit count, mix, unclassified). Do not edit the JSON by hand.
Then run `npm test` again (the kiro tests read this file).

## 5. Commit

Make one commit with steps 2 to 4 plus one new log line at the end of the latest week in `KIRO.md`:

`2026-11-28 | Fadil | kiro-proof (chat) PR #31 review fixes | <what you did, test counts> | review by Claude Code found the merge conflicts with main and the Kiro tab being hidden behind the Load screen; nothing typed by hand`

Commit message:

```
kiro-proof/7: merge main, Kiro tab skips the recording gate, refresh timeline

Kiro: vibe
```

Do not add any Co-Authored-By line or any other trailer. Do not push. At the end print `git log --oneline -3`
and `git status --short`.
