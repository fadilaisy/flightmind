# Requirements: upload-ui (SCRUM-66)

An analyst brings their own ASTERIX recording. The server side (SCRUM-62 contract and mock, then the real API) is not built yet, so this spec covers the web side against a temporary client and an in-browser mock.

## R1 Empty state
When the URL has no `?recording=` and no recording is ready, the app shows the Load screen (Figma frame 1, `32:1632`): a drop zone with a "Choose file" button. It accepts .pcap, .pcapng, .atx, .ast and .bin files up to 2 GB. For .atx, .ast and .bin it asks for "Recording date", defaulting to the file's last-modified date.

## R2 Upload
The app creates the recording (`POST /api/recordings`), then sends slices of `part_size_bytes` with `PUT /api/recordings/{id}/parts/{n}`, one after another. A failed part is retried up to 3 times. The screen shows bytes sent across all parts (for example "48.0 of 312.0 MB"). After the last part the app calls `POST /api/recordings/{id}/complete`.

## R3 Progress
The app polls `GET /api/recordings/{id}` every 2 s and shows the stage (Uploading, Scanning, Decoding, Filtering, Detecting events, Storing) with records_done / records_total when present. When the status is `scanned` and exactly one stream is supported, the app calls `process` with that stream automatically (SCRUM-69 adds the stream picker). When the status is `ready`, the app sets `?recording=<id>` and opens Events.

## R4 Failure
A `failed` recording shows `Recording.error` as written and a "Try another file" button. A 413 shows "This file is larger than 2 GB." A 415 shows "FlightMind reads .pcap, .pcapng, .atx, .ast and .bin files."

## R5 Header and picker
"Load recording" in the header is enabled. It opens a panel with the drop zone and a list from `GET /api/recordings` (filename, size, date, status chip). Picking a ready recording sets `?recording=<id>`. The header shows the selected recording's filename.

## R6 Recording in the URL
The selected id lives in `?recording=` and is sent as the `recording` query to events, tracks and stream, as `recording_id` to ask, and as the path id to compression. A reload keeps it.

## R7 Wording
Sentence case, no all-caps labels, units on every number (`.kiro/steering/ui.md`).

## R8 Visual check
Screenshots of the empty, uploading, processing, failed and picker states at 1440 x 900 are compared with Figma frame 1 before the last task is ticked.

## Out of scope
The stream picker (SCRUM-69), the real server (SCRUM-62), resuming an interrupted upload.
