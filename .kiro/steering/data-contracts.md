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
- **C6 clock:** `clock.now()` everywhere; replay is the only required mode.
- `raw_ref` format: `<recording_file_id>:<record_index>`.
- After a contract change, regenerate `contracts/types.ts`; never edit it by hand.
