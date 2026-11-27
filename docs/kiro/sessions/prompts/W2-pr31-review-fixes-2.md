# PR #31 review fixes, round 2

Same worktree and branch (`role1/scrum-70-built-with-kiro`). Do not switch branches and do not push.
Review of commit 164f564 found two problems.

## 1. The timeline was generated before the merge

`web/src/kiro/timeline.json` has `"head": "a9cc224..."` and 126 commits, so it was built from the pre-merge HEAD.
The branch now has 140 non-merge commits (`git rev-list --no-merges --count HEAD`), including the upload-ui and
load-page commits from main. Regenerate it last, after step 2 is committed or staged, with `npm run kiro:timeline`
from `web/`. Then check: `head` is not a9cc224, the commit count equals `git rev-list --no-merges --count HEAD`
at the moment you run it, and commits such as `7ff03cd` and `864a5c9` appear. Report the printed line.

## 2. Each date must appear once in the timeline

The duplicate-key error came from the day grouping in `KiroView.tsx`: it only merges *consecutive* commits with the
same date, and git log order (by commit date, across merged branches) does not keep author dates together. Keying by
index hides the error but shows the same date heading two or more times. Fix it properly:

- Group commits by `date` with a Map so each date has exactly one group, then order the groups by date, newest
  first. Inside a group keep the order they arrive in.
- Put the key back to `key={d.date}`.
- Add a test in `web/tests/kiro.test.tsx` with three commits whose dates go 2026-11-26, 2026-11-25, 2026-11-26 in
  that order, and check that the page shows two day headings (2026-11-26 first, then 2026-11-25) with two commits under 2026-11-26.

Run `npm test` and `npm run build` from `web/`. Both must pass.

## 3. Commit

Add `docs/kiro/sessions/prompts/W-pr31-review-fixes.md` and this file. One commit:

```
kiro-proof/7: one heading per day in the Kiro timeline, regenerate it after the merge

Kiro: vibe
```

No Co-Authored-By line and no other trailer. Do not push. Print `git log --oneline -3` and `git status --short` at the end.
