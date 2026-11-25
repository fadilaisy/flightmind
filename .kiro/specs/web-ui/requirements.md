# Requirements: web-ui (SCRUM-39)

Scope: Map view (default), 3D tab, Records tab. Built against the mock API served from
`fixtures/`. Rules: `.kiro/steering/ui.md`. Types: `contracts/types.ts` only.

Design source: Figma "Prototype v2 · light"
(https://www.figma.com/design/RSgriaKxz59KrI9eWvrsr0). Not read yet; see Open items.

## Glossary
- **Kept point:** a track point with `kept_for_event` false or absent.
- **Event window:** points between an event's `start_ts` and `end_ts`.
- **Flagged window:** an event window the detector marked, shown as "flagged window".
- **Scrubber:** the shared time control. Its value is one timestamp.

## R1. App shell and tabs
1. The app shows three top tabs: Events, Trajectory, Records. Trajectory is selected on load. A Map / 3D / Profile toggle sits inside Trajectory.
2. The selected tab is kept in the URL so a link reopens it.
3. All labels use sentence case. No all-caps labels, no trailing arrows.
4. The header shows `mode` and `sim_time` from `/api/meta`, with a "sample data" label while the mock API is used.

## R2. Data access
1. The web app calls only endpoints in `contracts/openapi.yaml`: `/api/meta`, `/api/events`, `/api/events/{id}`, `/api/tracks/{icao24}`, `/api/raw/{raw_ref}`.
2. Request and response types come from `contracts/types.ts`. No hand-written copies.
3. A base-URL setting switches between the mock API and the real API with no code change.
4. A failed request shows the status and the URL. A 404 on `/api/raw/{raw_ref}` shows "Record not found: <raw_ref>".

## R3. Map view
1. The map shows a basemap and a WIII runway layer.
2. Each track point is drawn at `lat`, `lon`.
3. A point has one of three styles: kept, event window, flagged. The legend names all three.
4. The user picks an aircraft from the event list. The track loads from `/api/tracks/{icao24}`.
5. Selecting an event zooms to its window and marks the flagged window.
6. Hovering a point shows `ts` (as I021/071), `lat`, `lon`, `alt_ft` with unit and datum, and `raw_ref`.
7. Clicking a point opens its record in the Records tab.
8. The list of events shows state: "To review", "Confirmed by you" or "Dismissed by you". The state starts as "To review" and is kept in the browser only.

## R4. Charts and scrubber
1. Three charts sit under the map: altitude, speed, vertical rate. They share one time axis.
2. Altitude is `alt_ft`. Speed and vertical rate are computed in the browser from consecutive points. Each chart title says "computed from positions" for these two.
3. A gap in `alt_ft` (null) shows as a gap in the line, not as zero.
4. The scrubber moves one cursor across the map and all three charts.
5. Dragging the scrubber moves a marker on the map to the nearest point at or before the scrubber time.
6. Keyboard: left and right arrows step one point. Shift steps ten.
7. The flagged window is shaded on the scrubber and on all three charts.

## R5. 3D tab
1. The tab draws the track as a line in lon, lat, altitude, with the same three point styles.
2. The same scrubber and selected point apply. A change in one tab shows in the others.
3. The altitude scale is labelled with its exaggeration factor.

## R6. Records tab
1. The tab shows a tree: Block > Record > Item.
2. Selecting a point or a `raw_ref` loads `/api/raw/{raw_ref}`.
3. Each item shows its I021 number, name, decoded value, unit, LSB and datum where the item has one.
4. A hex pane and an ASCII pane show the record bytes from `hex`.
5. Selecting an item highlights its bytes in both panes. Selecting bytes highlights the item.
6. Every row shows its offset. The record header shows `raw_ref`, `sac`, `sic`.
7. The time item is I021/071 everywhere.

## R7. Wording and evidence
1. Text says what the data shows. Use "flagged window". Use "no on-ground flag (I021/040) was set". Never "went around" or "no touchdown".
2. Every number or claim on screen links to a `raw_ref`.
3. Numbers show unit and datum, for example "1,250 ft, WGS-84".

## R8. Quality
1. Palette, spacing and shadows follow the Figma file. Shadows are soft.
2. The first screen is usable at 1366 x 768.
3. A track of 5,000 points draws and scrubs without visible lag.

## Open items
1. Figma is now read through the remote Figma MCP. The "Foundations" page is read: palette, type and screen map are in `design.md`. The "Screens" page frames (5, 5b, 6, 7, 7b, 9) are not read yet; layout needs one pass with `get_design_context` per frame.
1a. Figma conflicts with `ui.md`: the type scale has a caps label style, the sample headline says "went around", and the screen map lists `GET /api/compression/{id}` and a replay endpoint, which are not in `contracts/openapi.yaml`. `ui.md` wins; Role 1 confirms.

## Figma frames in scope
| Frame | Covers |
| --- | --- |
| 5 Trajectory, Map (default) | R3, R4 |
| 5b Trajectory, 3D (toggle) | R5 |
| 6 Event panel | R3.5, R3.8 |
| 7 Raw record viewer | R6 |
| 7b Raw record, Wireshark-style | R6.1 to R6.5 |
| 9 Records (raw evidence) | R6 |

Frames 1 to 4 and 8 (load, preview, clean, events review, export) are out of scope for SCRUM-39.
The overview shows an event list on the left, the map in the middle, a panel on the right, and the charts with the scrubber at the bottom. The 3D view is a toggle inside the Trajectory screen. The Records tab is its own screen, and the record viewer also opens as a dialog.
2. Zahran's mock API (SCRUM-33, `services/intel/mock_api`) is on main and serves `contracts/openapi.yaml` with CORS on. Local dev: run it with uvicorn on port 8000 and set `VITE_API_BASE=http://localhost:8000`. `web/tests/fixtures/mini.json` stays for unit tests only.
3. The contract has no block or frame data. R6 shows one block with one record until the contract has more. `raw_ref` has no item offsets, so item offsets come from the decoded record.
4. The contract has no speed or vertical rate. R4.2 computes them. This is a guess to confirm.
5. The contract has no flag for "event window" per point. Only `kept_for_event` exists. The window is computed from the event `start_ts` and `end_ts`.
6. `/api/stream` is not used. Replay is the scrubber.
7. The WIII runway geometry is not in the contract. It is a static file in `web/`.
8. Compression size display waits for GET /api/compression/{recording_id} (SCRUM-60).
