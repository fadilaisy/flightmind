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

- [x] 7. Contract additions 6.1
  - Files: `web/src/api/uploadTypes.ts`, `client.ts`, `mockClient.ts`, `web/src/domain/zip.ts`, `web/tests/uploadPlan61.test.ts`
  - Check: preview, recipe, quarantine and export in client and mock; two streams for pcap, stream "raw" for raw files; set_aside counts add up; zip has 4 files.

- [x] 8. Stream pick (Load)
  - Files: `web/src/views/StreamsView.tsx`, `LoadView.tsx`, `web/src/domain/upload.ts`
  - Check: scanned recording shows "UDP streams found", "Use" and "not supported yet"; "Decode CAT021 stream" opens the preview; raw file goes straight to the preview; no auto-process.

- [x] 9. Decoded preview
  - Files: `web/src/views/PreviewView.tsx`, `web/src/domain/preview.ts`
  - Check: 8 records, field quality bars, "sample of N records", "Continue to cleaning", raw_ref chips open the record dialog.

- [x] 10. Clean and reduce
  - Files: `web/src/views/CleanView.tsx`, `web/src/components/QuarantineList.tsx`, `StageList.tsx`, `web/src/domain/recipe.ts`
  - Check: recipe steps with counts, paged quarantine list, tolerance_note as text, sizes and ratio, "Apply and find events" shows stages then opens Events.

- [x] 11. Export, tabs and header fixes
  - Files: `web/src/views/ExportView.tsx`, `Shell.tsx`, `web/src/App.tsx`
  - Check: four files listed, "Export 4 files" downloads the zip; tabs Load, Preview, Clean, Events, Trajectory, Records, Export with `?tab=`; Load tab active on the Load screen; "sample data" only when the sample dataset is shown.

- [x] 12. Tests and screenshots
  - Files: `web/tests/steps.test.tsx`, `docs/kiro/figma-check/69-*.png`
  - Check: scanned, preview, process, ready covered; screenshots at 1440 x 900 next to the Figma PNGs in `figma-check/ref/`.