# Example: a Kiro CLI prompt (SCRUM-66 upload screen)

Fadil wrote this prompt and ran it with `kiro-cli chat --no-interactive`; Kiro wrote the upload-ui spec and implemented its tasks, committing one step at a time (see the upload-ui lines in KIRO.md). `<temp>` stands for a local temp folder.

# Kiro prompt U: SCRUM-66 load recording screen, chunked upload, recording picker

Branch `role1/upload-ui` (already created from main). Work only in `web/`, `.kiro/specs/upload-ui/`, `KIRO.md` and `docs/kiro/`. Do not touch `contracts/`, `services/`, `.kiro/agents/` (never `git add` its change or the `.bak` file) or `.kiro/settings/mcp.json`. A dev server runs at http://127.0.0.1:5173 with hot reload; do not start another or stop it.

## Context
FlightMind must let an analyst bring their own ASTERIX recording. The server side (SCRUM-62 contract and mock, then the real API) is not built yet. So for now:
- Put temporary types for the new contract in `web/src/api/uploadTypes.ts`, matching the contract below exactly, with a comment that they get replaced by `contracts/types.ts` once SCRUM-62 merges.
- Add the new calls to `web/src/api/client.ts` (real HTTP) and to `web/src/api/mockClient.ts` (the in-browser mock used when `VITE_API_BASE` is empty). The mock accepts and discards the bytes, then moves a recording through the stages over about 10 seconds to `ready`, returns the existing sample dataset for any ready id, and can be made to fail (for example a file named `bad.pcap` ends in `failed` with error "No CAT021 records found in bad.pcap"; a 3 GB size gives 413; a `.txt` gives 415).

Contract (from the upload plan, section 1):
```
POST /api/recordings                    JSON {filename, size_bytes, recording_date?}
  201 -> Recording (status "uploading"), part_size_bytes = 52428800
  413 -> size over 2048 MB;  415 -> extension not .pcap .pcapng .atx .ast .bin
PUT  /api/recordings/{id}/parts/{n}     raw bytes of part n (0-based) -> 204; 409 out of order
POST /api/recordings/{id}/complete      -> 202 Recording (status "scanning", then "scanned" with streams);
                                          200 existing Recording when the same sha256 was uploaded before;
                                          415 first bytes are not pcap, pcapng or ASTERIX CAT021
POST /api/recordings/{id}/process       JSON {stream_id} -> 202, status "queued"
GET  /api/recordings                    -> Recording[] newest first
GET  /api/recordings/{id}               -> Recording; 404 unknown
Recording: id ("r" + 10 hex), filename, size_bytes, bytes_received, part_size_bytes,
  format [pcap, pcapng, asterix_raw], status [uploading, scanning, scanned, queued, decoding, filtering,
  detecting, storing, ready, failed], progress {records_done, records_total} | null, error | null,
  record_count, event_count, first_ts, last_ts (null until ready), created_at,
  streams: [{id, src, dst, category, sac, sic, frames, records, supported}] (set when scanned)
Existing endpoints gain an optional `recording` query (events, tracks, stream), AskRequest.recording_id,
and /api/compression/{recording_id} is already keyed.
```

## Visual target
Figma frame 1 "Load a recording" (`32:1632`), exported at `<temp>\figma-upload\figma-1-load.png`, and the `s-load` screen in `docs/design/prototype-v2.html` (open it and run `go('load')`). Figma wins on visuals; `.kiro/steering/ui.md` wins on wording (sentence case, no all-caps, units on every number). Use the existing tokens, app bar, buttons and `StateBox`.

## Steps
0. Write a short spec in `.kiro/specs/upload-ui/` (requirements.md, design.md, tasks.md) from the SCRUM-66 acceptance criteria below, with numbered tasks. Commit it (trailer `Kiro: spec upload-ui/0`).
1. Types and API: `uploadTypes.ts`, client and mock calls as above, plus `recording` passed to events, tracks, stream, ask (`recording_id`) and compression. Unit tests for the mock's stage progression and the 413/415/failed cases.
2. Empty state: when there is no `?recording=` in the URL and no ready recording, the app shows the Load screen like frame 1: drop zone with "Choose file", accepts .pcap, .pcapng, .atx, .ast, .bin up to 2 GB. For .atx/.ast/.bin ask "Recording date", default the file's last-modified date.
3. Upload: create, then send `part_size_bytes` slices (`File.slice`) with PUT one after another, retrying a failed part up to 3 times; show bytes sent across all parts (e.g. "48.0 of 312.0 MB"). Then complete, and poll `GET /api/recordings/{id}` every 2 s. When `scanned` and exactly one stream is supported, call process with it automatically (SCRUM-69 adds the stream picker). Show the stage (Uploading, Scanning, Decoding, Filtering, Detecting events, Storing) with records_done / records_total. On ready, set `?recording=<id>` and open Events.
4. Failed: show `Recording.error` as written and a "Try another file" button. 413 and 415 get their own sentence ("This file is larger than 2 GB." / "FlightMind reads .pcap, .pcapng, .atx, .ast and .bin files.").
5. Header: enable "Load recording". It opens a panel with the drop zone and a list from `GET /api/recordings` (filename, size, date, status chip); picking one sets `?recording=<id>`. The header shows the selected recording's filename instead of rec01. Reload keeps it.
6. Tests for polling, part retry and error states. Then screenshot each state (empty, uploading, processing, failed, picker) at 1440 x 900, compare with `figma-1-load.png`, fix differences, save as `docs/kiro/figma-check/66-*.png`.

After each step: `npm run build` and `npm test` pass in `web/`, tick the task in `.kiro/specs/upload-ui/tasks.md`, add one KIRO.md line (role Fadil, spec/task `upload-ui/<n>`), commit only that step's files with message `upload-ui/<n>: <what>` and the trailer line `Kiro: spec upload-ui/<n>`. No other trailers.

## SCRUM-66 acceptance criteria (for the spec)
- Empty state with drop zone and "Choose file"; accepts .pcap, .pcapng, .atx, .ast, .bin up to 2 GB; raw files ask for "Recording date" defaulting to the file's modified date.
- Upload calls create, sends part_size_bytes slices with PUT one after another, retries a failed part up to 3 times, shows bytes sent across all parts, then calls complete.
- Progress shows the stages with records_done / records_total, polling every 2 s.
- Failed state shows Recording.error as written with "Try another file"; 413 and 415 get their own sentence.
- "Load recording" in the header opens the drop zone and a picker from GET /api/recordings (filename, size, date, status).
- The selected id lives in ?recording= and is sent to events, tracks, stream, ask and compression; reload keeps it.
- Until the stream screen exists, a scanned recording with one supported stream calls process automatically.
- Screenshot at 1440 vs Figma frame 1 before ticking.

Finish with build and tests passing and print what you committed and what is left.
