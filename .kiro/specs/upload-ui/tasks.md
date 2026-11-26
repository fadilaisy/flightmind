# Tasks: upload-ui

- [x] 0. Spec
  - Files: `.kiro/specs/upload-ui/`
  - Reqs: R1 to R8

- [x] 1. Types and API
  - Files: `web/src/api/uploadTypes.ts`, `client.ts`, `mockClient.ts`, `web/tests/uploadApi.test.ts`
  - Check: mock stage progression, 413, 415 and failed cases tested; `recording` passed to events, tracks, stream, ask and compression.
  - Reqs: R2, R3, R4, R6

- [x] 2. Empty state
  - Files: `web/src/views/LoadView.tsx`, `web/src/App.tsx`, `strings.ts`
  - Check: Load screen with drop zone, "Choose file", accepted extensions, "Recording date" for raw files.
  - Reqs: R1, R7

- [x] 3. Upload and progress
  - Files: `web/src/domain/upload.ts`, `LoadView.tsx`
  - Check: part slices, bytes sent, stages with records, polling every 2 s, automatic process, `?recording=` set on ready.
  - Reqs: R2, R3, R6

- [x] 4. Failed state
  - Files: `LoadView.tsx`
  - Check: error text as written, "Try another file", 413 and 415 sentences.
  - Reqs: R4

- [x] 5. Header and picker
  - Files: `web/src/views/Shell.tsx`, `web/src/components/RecordingPicker.tsx`
  - Check: button enabled, list from GET /api/recordings, picking sets `?recording=`, filename in the header, reload keeps it.
  - Reqs: R5, R6

- [x] 6. Tests and screenshots
  - Files: `web/tests/upload.test.ts(x)`, `docs/kiro/figma-check/66-*.png`
  - Check: polling, part retry and error-state tests pass; five screenshots compared with frame 1.
  - Reqs: R8
