# Tasks: web-ui (SCRUM-39)

Do not implement until the spec is approved. Tick a box only when the check passes. After each ticked task, add a line to `KIRO.md`.
Paths are under `web/` unless noted.
For every task that builds a view or component (3, 6, 7, 8, 10, 11, 12, 14, 15), first read the matching Figma frame through the Figma MCP, as `.kiro/steering/ui.md` says. A task's check also needs the view to match its frame, or the KIRO.md line lists the differences.

- [x] 1. Scaffold the app
  - Files: `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`
  - Check: `npm run dev` opens a blank page; `npm run build` passes.
  - Reqs: R1

- [x] 2. API client, types and mock
  - Files: `src/api/types.ts`, `src/api/client.ts`, `src/api/mockClient.ts`, `tests/fixtures/mini.json`
  - Check: a test loads `/api/meta`, `/api/events`, one track and one raw record, typed with `contracts/types.ts`. A 404 gives "Record not found: <raw_ref>". Base URL switches by env var.
  - Reqs: R2

- [x] 3. Tokens and shell with tabs
  - Files: `src/styles/tokens.css`, `src/strings.ts`, `src/views/Shell.tsx`
  - Check: top tabs Events, Trajectory, Records; Trajectory is the default; a Map / 3D / Profile toggle sits inside Trajectory; the tab shows in the URL; header shows mode, sim_time and "sample data".
  - Reqs: R1, R8.1

- [x] 4. Store
  - Files: `src/state/store.ts`
  - Check: unit test: setting `scrubTs` or `rawRef` updates all subscribers; event state survives a reload.
  - Reqs: R3.8, R4.4, R5.2

- [x] 5. Point style and window logic
  - Files: `src/domain/pointStyle.ts`, `src/domain/window.ts`, `tests/pointStyle.test.ts`
  - Check: tests cover flagged, event window and kept; a point on the window edge counts as inside.
  - Reqs: R3.3

- [x] 6. Event list with states
  - Files: `src/components/EventList.tsx`
  - Check: list shows type, callsign, window, state; the three state buttons work; a click selects the event.
  - Reqs: R3.4, R3.8

- [x] 7. Map with basemap and WIII runway
  - Files: `src/views/MapView.tsx`, `src/geo/wiii-runway.geojson`, `src/components/Legend.tsx`
  - Check: map shows the runway layer; legend lists kept, event window, flagged.
  - Reqs: R3.1, R3.3

- [x] 8. Track points on the map
  - Files: `src/views/MapView.tsx`, `src/domain/format.ts`
  - Check: points draw in three styles; hover shows `ts`, lat, lon, altitude with unit and datum, `raw_ref`; selecting an event zooms to its window.
  - Reqs: R3.2, R3.5, R3.6, R7

- [x] 9. Derived speed and vertical rate
  - Files: `src/domain/derive.ts`, `tests/derive.test.ts`
  - Check: tests with known points give the expected kt and ft/min; null altitude gives null; a step under 0.5 s gives null.
  - Reqs: R4.2, R4.3

- [x] 10. Charts
  - Files: `src/components/Charts.tsx`
  - Check: three charts share one time axis; null altitude shows a gap; the flagged window is shaded; titles for speed and vertical rate say "computed from positions".
  - Reqs: R4.1, R4.2, R4.3, R4.7

- [x] 11. Scrubber
  - Files: `src/components/Scrubber.tsx`, `tests/scrubber.test.tsx`
  - Check: drag and arrow keys move the cursor on map and charts; Shift moves ten points; the marker sits on the nearest point at or before the time.
  - Reqs: R4.4, R4.5, R4.6

- [x] 12. 3D tab
  - Files: `src/views/ThreeDView.tsx`
  - Check: line and points in three styles; marker follows the scrubber; exaggeration factor shown; a 5,000-point track scrubs without lag.
  - Reqs: R5, R8.3

- [x] 13. Item metadata table
  - Files: `src/domain/itemMeta.ts`, `tests/itemMeta.test.ts`
  - Check: I021/071 and I021/040 have name, unit, LSB and datum where they apply; unknown items return the raw value only.
  - Reqs: R6.3, R6.7

- [ ] 14. Records tree and header
  - Files: `src/views/RecordsView.tsx`, `src/components/RecordTree.tsx`
  - Check: clicking a map point opens its record; header shows `raw_ref`, `sac`, `sic`; items show unit, LSB, datum.
  - Reqs: R6.1, R6.2, R6.3, R6.6

- [ ] 15. Hex and ASCII panes with linked highlight
  - Files: `src/components/HexPane.tsx`, `tests/hexpane.test.tsx`
  - Check: rows of 16 with offsets; selecting an item highlights its bytes in both panes; selecting bytes highlights the item.
  - Reqs: R6.4, R6.5

- [ ] 16. Wording check
  - Files: `src/strings.ts`, `tests/wording.test.ts`
  - Check: the test fails if "went around" or "no touchdown" appears; "no on-ground flag (I021/040) was set" is used where the flag is absent; no all-caps labels.
  - Reqs: R1.3, R7

- [ ] 17. Smoke test and Figma pass
  - Files: `tests/smoke.test.ts`
  - Check: the mock loads, each tab opens, no console errors; a person compares each view with the Figma page and logs differences in `docs/kiro/clips.md` or an issue.
  - Reqs: R8

- [ ] 18. README and library list
  - Files: `README.md` (web section)
  - Check: lists MapLibre GL, three.js, uPlot and any other library that does real work.
  - Reqs: tech steering rule

- [ ] 19. Compression before/after size (blocked on SCRUM-60)
  - Files: `src/components/CompressionBadge.tsx`
  - Check: shows raw and stored point counts and sizes for the recording from GET /api/compression/{recording_id}, once that endpoint is in `contracts/openapi.yaml`. Until then, show nothing. Don't add the endpoint here.
  - Reqs: product steering, headline 2
