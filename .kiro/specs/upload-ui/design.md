# Design: upload-ui

## API
- `web/src/api/uploadTypes.ts`: temporary types for the SCRUM-62 contract (Recording, RecordingStream, RecordingStatus, request bodies). Replaced by `contracts/types.ts` once SCRUM-62 merges.
- `Api` gains `createRecording`, `uploadPart`, `completeRecording`, `processRecording`, `listRecordings`, `getRecording`, `compression`, `streamUrl`. `events`, `track` and `ask` take an optional recording id.
- `httpApi` calls the endpoints. `ApiError.status` carries 413, 415, 409 and 404.
- `mockApi` accepts and discards bytes. A recording moves uploading, scanning, scanned, then (after `process`) decoding, filtering, detecting, storing, ready over about 10 s, with the time source injectable for tests. `bad.pcap` ends in `failed` with "No CAT021 records found in bad.pcap". A size over 2048 MB gives 413 and a `.txt` gives 415. Every ready id returns the sample dataset.

## Domain (`web/src/domain/upload.ts`)
- `checkFile(name, size)`: extension and size check before any call.
- `uploadRecording(api, file, date, onProgress)`: create, slices with `File.slice`, retry 3 times, complete. No timers, so tests run it directly.
- `stageLabel(status)`, `formatMb(bytes)`.
- `nextAction(recording)`: poll, process(stream), done or failed. Pure, so the polling loop is tested without React.

## UI
- `views/LoadView.tsx`: the Load screen (frame 1) and its states: choose, uploading, processing, failed. `components/RecordingPicker.tsx`: the header panel.
- `domain/recordingParam`: `?recording=` read through `useUrlParam`, written through `navigate`.
- `App.tsx`: no `?recording=` and no ready recording shows LoadView. With `VITE_API_BASE` empty, the mock lists the sample recording as ready, so the sample flow keeps working through the picker.
- `Shell` header: enabled button, filename of the selected recording.

## Checks
Unit tests for the mock stages and errors, retry, polling and the error states. Screenshots in `docs/kiro/figma-check/66-*.png`.
