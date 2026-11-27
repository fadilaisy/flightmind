---
inclusion: fileMatch
fileMatchPattern: ["contracts/**", "services/**"]
---
# Data contracts

The source of truth is `contracts/schema.sql` and `contracts/openapi.yaml`. This file
explains the rules; if they disagree, the contract files win and this file gets fixed in
the same pull request.

- **C1 `telemetry`:** one clean CAT021 point per row. Required: `ts`, `icao24`, `raw_ref`.
- **C2 `weather_reports`:** optional, cut list. Do not build features that need it.
- **C3 `events`:** one row per detected event, with `raw_refs` for every record used.
  Insert triggers `NOTIFY events_new`.
- **C4 `event_embeddings`:** one vector per event story.
- **C5 HTTP API:** as in `openapi.yaml`. Citations are `{kind, id, label}`; kind is
  `cat021_record` (id = raw_ref) or `event` (id = event uuid).
- **C5 compression report:** `GET /api/compression/{recording_id}` returns the `CompressionReport` with raw and stored size; `events_kept` must equal `events_total`. A recording with `raw_bytes` 0 returns 404, not a report with a made-up ratio.
- **C5 upload (v1.2, SCRUM-62):** `POST /api/recordings`, then `PUT .../parts/{n}` in
  order (50 MB parts, because the Cloudflare tunnel refuses requests over 100 MB), then
  `POST .../complete`, `POST .../process` with the chosen CAT021 stream. Status runs
  `uploading → scanning → scanned → queued → decoding → filtering → detecting → storing →
  ready`, or `failed` with a one-sentence `error`. Preview, recipe and quarantine work from
  `scanned` on; export only when `ready`. The same file twice (same sha256) returns the
  first upload. `/api/events`, `/api/tracks`, `/api/stream` take an optional `recording`
  filter (raw_ref starts with `<recording>:`), and `AskRequest` an optional `recording_id`.
- **C6 clock:** `clock.now()` everywhere; replay is the only required mode.
- **C7 `uploads` (Role 3):** one row per uploaded recording; mirrors the `Recording` schema.
- **C8 `quarantine` (Role 2):** records the cleaning set aside, with step and reason.
- `raw_ref` format: `<recording_file_id>:<record_index>`. For an upload, the id is the
  server-made `uploads.id` (`r` + 10 hex digits), not the file name.
- After a contract change, regenerate `contracts/types.ts`; never edit it by hand.
