# Kiro prompt: Load page with capability panel and recent recordings

Branch: `role1/load-page-capabilities`, new from latest `main`. Visual target: `/mnt/project-files/flightmind/reviews/load-page-combined-v2.png` (copied into the repo as `docs/design/load-page-combined-v2.png`).

---

Go. On a new branch `role1/load-page-capabilities` from the latest `main`, rework the Load screen (`web/src/views/LoadView.tsx`, "choose" phase only) to match `docs/design/load-page-combined-v2.png`. Do not stop to ask; finish, test, commit and push.

**Layout, top to bottom (choose phase):**
1. Title "Load a recording" (left aligned, not centred).
2. The drop zone (`DropZone`), one line: bold "Drop a CAT021 file" followed by grey ".pcap, .pcapng, .atx, .ast · up to 2 GB", then the Choose file button (solid blue). Keep the file icon. Keep drag and drop, the hidden input, `ACCEPTED_EXTENSIONS` and `checkFile` exactly as they are.
3. Section "What FlightMind analyzes": four cards in one row (stack to 2x2 under 900 px), each a bold title and one grey sentence. Use exactly this wording (put it in `strings.ts`):
   - **Aircraft tracks**: "Groups CAT021 reports by aircraft (ICAO address) into one track each."
   - **Flight events**: "Flags go-arounds, holdings and squawk 7500, 7600, 7700, with why each was flagged."
   - **4D trajectories**: "Position, altitude and time on a map, in 3D, or as a profile."
   - **Raw records**: "Every claim cites the decoded record and its bytes."
4. Section "Recent recordings" with grey "from this server" on the right. A white bordered list, newest first, at most 5 rows, from `api.listRecordings()`. Each row: filename in mono, grey meta line (size · date from `recordingDate()`, plus `record_count` as "1,420,318 records" when known, plus `error` for failed rows), a middle column, the `statusChip()` badge, and an action on the right:
   - ready: middle "N events" in amber (from `event_count`, "1 event" singular, hide if null); action "Open →" calls the same handler the picker uses to open a recording (`onReady(id)` / `chooseRecording`).
   - processing (any status that isn't ready/failed/uploading): middle shows `stageLabel(status)` and a thin progress bar from `progress.records_done / records_total` (no bar if progress is null); action "Follow →" follows it in this view the way `follow` does.
   - failed: middle "–"; action "Details" shows the error inline under the row.
   - uploading: same as processing, label "Uploading".
   Loading, empty ("No recordings yet. Drop a file above to start.") and error states with Retry, using `StateBox`. Reuse `statusChip`, `recordingDate`, `formatSize`, `stageLabel` from `RecordingPicker`/`domain/upload`; export what you need, don't copy logic.

**Remove** from the choose phase: the intro paragraph (`loadIntro`), the three step cards (`loadsteps`, step1..3 strings) and the "What is CAT021?" footer. Delete their unused strings and CSS. The date, working, and failed phases stay as they are.

**Rules:**
- No new endpoints. Only `listRecordings()` and fields already in `Recording`. Never show invented rows.
- Never say "local" or "processed on your computer": files upload to the server.
- Light theme tokens from `web/src/styles/tokens.css` only; content width 880 px; left aligned sections; 24 to 32 px between sections.
- All text in `strings.ts`; update `wording.test.ts` if needed.

**Tests:** in `web/tests/upload.test.tsx` (or a new `loadPage.test.tsx`): the four capability cards render; the list renders a ready row with "3 events" and Open; a processing row with Follow; a failed row with Details showing the error; empty and error states; Open calls `onReady` with the id. `npm run build` and `npm test` pass.

**Check visually:** run the app with the mock (`npm run dev`), screenshot the Load tab at 1440 px wide, save it as `docs/design/load-page-built.png`, and compare with `docs/design/load-page-combined-v2.png`. Fix differences in spacing, alignment and type before committing.

**Finish:** one KIRO.md line, commit with trailer `Kiro: vibe`, no Co-Authored-By lines, push the branch, and open a PR to `main` titled "Load page: capability panel and recent recordings".
