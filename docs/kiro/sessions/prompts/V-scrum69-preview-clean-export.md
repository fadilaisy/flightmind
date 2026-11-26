# Kiro prompt V: SCRUM-69 stream pick, decoded preview, clean and reduce, export

Branch `role1/upload-ui` (continues after SCRUM-66 in the same branch). Same folder rules as before: only `web/`, `.kiro/specs/upload-ui/`, `KIRO.md`, `docs/kiro/`; never `contracts/`, `services/`, `.kiro/agents/`, `.kiro/settings/mcp.json`. Dev server at http://127.0.0.1:5173 already runs.

## Contract additions (upload plan 6.1), still only in the temporary `web/src/api/uploadTypes.ts`, client and in-browser mock
```
GET  /api/recordings/{id}/preview?stream=<id>&limit=8
     -> { records: RawRecord[], field_quality: [{ item: "I021/130", label, present_pct }], sample_size?: number }
POST /api/recordings/{id}/process       JSON { stream_id } -> 202, status "queued"   (already added)
GET  /api/recordings/{id}/recipe        -> { input_sha256, steps: [{ code, label, records_in, set_aside, reason }],
                                             tolerance_note, raw_bytes, stored_bytes, ratio }
GET  /api/recordings/{id}/quarantine?offset&limit -> { total, items: [{ raw_ref, step_code, reason }] }
GET  /api/recordings/{id}/export        -> application/zip: cleaned.csv, events.csv, quarantine.csv, recipe.json
```
Mock: two sample streams for pcap uploads (one CAT021 supported, one CAT062 "not supported yet"), one stream id "raw" for raw files; preview from the sample raw records with field quality for I021/130, 140, 145, 170, 040; a recipe with 3 to 4 steps whose set_aside counts add up; quarantine items with real sample raw_refs; export builds a small zip in the browser (a tiny store-only zip writer is fine; no new dependency unless one is already installed) with the 4 files.

## Visual targets (Figma page "Prototype v2 · light", Figma wins on visuals, ui.md on wording)
Exported at `<temp>\figma-upload\`:
`figma-1-load.png` (streams table part), `figma-2-preview.png`, `figma-3-clean.png`, `figma-8-export.png`, `figma-8b-quarantine.png`. Also prototype v2 screens `s-load`, `s-preview`, `s-clean`, `s-export` in `docs/design/prototype-v2.html`.

## Steps (add them as tasks to `.kiro/specs/upload-ui/tasks.md` first)
1. Load streams: when the recording is `scanned`, show the "UDP streams found" table (source → destination, category, SAC/SIC, frames, records), "Use" on supported rows and "not supported yet" on others; "Decode CAT021 stream" opens the preview. A raw file (single stream "raw") goes straight to the preview. Remove SCRUM-66's auto-process.
2. Decoded preview (frame 2): first 8 records from /preview and the field quality bars with present_pct; say "sample of N records" when sample_size is set; "Continue to cleaning".
3. Clean and reduce (frame 3): recipe steps from /recipe (label, set aside count, reason); each count opens the paged quarantine list (frame 8b layout) whose raw_ref chips open the raw record dialog. Show `tolerance_note` as text instead of the 10/25/50 m buttons (that choice is still open in SCRUM-67). Ratio and raw vs stored sizes. "Apply and find events" calls process, shows the stages, then opens Events.
4. Export (frame 8): list cleaned.csv, events.csv, quarantine.csv and recipe.json with what each holds and their sizes when known; "Export 4 files" downloads /export.
5. Tabs follow the prototype v2 flow: Load, Preview, Clean, Events, Trajectory, Records, Export. Preview, Clean and Export appear once a recording is selected. Keep `?tab=` in the URL.
6. Tests for scanned → preview → process → ready. Screenshot each screen at 1440 x 900 next to its Figma PNG, fix differences, save as `docs/kiro/figma-check/69-*.png`.

Cut order if you run short: quarantine list first (counts stay), then field quality bars (table stays). Never cut the stream pick, recipe counts or export.

After each step: build and tests pass, tick the task, one KIRO.md line, commit with message `upload-ui/<n>: <what>` and trailer `Kiro: spec upload-ui/<n>`. No other trailers. Finish by printing what you committed and what is left.

## Also fix from the SCRUM-66 review
- On the Load screen the Trajectory tab is underlined; the Load tab must be the active one.
- With no recording loaded the header still says "sample data"; show it only when the mock's sample dataset is what is on screen.

