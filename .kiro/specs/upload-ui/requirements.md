# Requirements: upload-ui (SCRUM-66)

An analyst brings their own ASTERIX recording. The server side (SCRUM-62 contract and mock, then the real API) is not built yet, so this spec covers the web side against a temporary client and an in-browser mock.

## R1 Empty state
When the URL has no `?recording=` and no recording is ready, the app shows the Load screen (Figma frame 1, `32:1632`): a drop zone with a "Choose file" button. It accepts .pcap, .pcapng, .atx, .ast and .bin files up to 2 GB. For .atx, .ast and .bin it asks for "Recording date", defaulting to the file's last-modified date.

## R2 Upload
The app creates the recording (`POST /api/recordings`), then sends slices of `part_size_bytes` with `PUT /api/recordings/{id}/parts/{n}`, one after another. A failed part is retried up to 3 times. The screen shows bytes sent across all parts (for example "48.0 of 312.0 MB"). After the last part the app calls `POST /api/recordings/{id}/complete`.

## R3 Progress
The app polls `GET /api/recordings/{id}` every 2 s and shows the stage (Uploading, Scanning, Decoding, Filtering, Detecting events, Storing) with records_done / records_total when present. The app never starts processing on its own: it stops polling at `scanned` and the analyst picks a stream (R9). When the status is `ready`, the app sets `?recording=<id>` and opens Events.

## R4 Failure
A `failed` recording shows `Recording.error` as written and a "Try another file" button. A 413 shows "This file is larger than 2 GB." A 415 shows "FlightMind reads .pcap, .pcapng, .atx, .ast and .bin files." A recording still `uploading` when this tab did not send its parts (opened from the picker or `?recording=<id>`) shows the failed state with "This upload did not finish. Try another file." and the same button, instead of polling.

## R5 Header and picker
"Load recording" in the header is enabled. It opens a panel with the drop zone and a list from `GET /api/recordings` (filename, size, date, status chip). Picking a ready recording sets `?recording=<id>`. The header shows the selected recording's filename.

## R6 Recording in the URL
The selected id lives in `?recording=` and is sent as the `recording` query to events, tracks and stream, as `recording_id` to ask, and as the path id to compression. A reload keeps it.

## R7 Wording
Sentence case, no all-caps labels, units on every number (`.kiro/steering/ui.md`).

## R8 Visual check
Screenshots of the empty, uploading, processing, failed and picker states at 1440 x 900 are compared with Figma frame 1 before the last task is ticked.

## R9 Stream pick (SCRUM-69)
When a recording is `scanned`, the Load tab lists the UDP streams found with src, dst, category, SAC/SIC and record count. A supported stream (CAT021) has a "Use" button; others read "not supported yet". "Decode CAT021 stream" opens the preview. A raw file has the single stream `raw` and goes straight to the preview. Nothing is processed without this choice.

## R10 Decoded preview
The Preview tab shows a sample of 8 decoded records ("sample of N records"), a quality bar per field, and `raw_ref` chips that open the record dialog. "Continue to cleaning" opens the Clean tab.

## R11 Clean and reduce
The Clean tab lists the clean recipe steps with counts and the quarantine (records set aside) as a paged list, with the `tolerance_note` as text. It shows sizes before and after and the ratio. "Apply and find events" shows the processing stages, then opens Events.

## R12 Export and tabs
The Export tab lists four files and "Export 4 files" downloads them as a zip. Tabs are Load, Preview, Clean, Events, Trajectory, Records, Export, kept in `?tab=`. The Load tab is active on the Load screen. "sample data" shows only when the sample dataset is shown.

## Out of scope
The real server (SCRUM-62), resuming an interrupted upload.
